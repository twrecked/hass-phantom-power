"""Sensor platform for Phantom Power."""
from __future__ import annotations

import datetime
import logging
import random
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ENTITY_ID,
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import (
    device_registry as dr,
    entity_platform,
    entity_registry as er,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util, slugify

from .const import (
    ATTR_ACTIVE_MEMBERS,
    ATTR_ACTIVE_RULE,
    ATTR_VARIANCE,
    CONF_ATTRIBUTE,
    CONF_CONTAINS,
    CONF_STATE,
    CONF_STATES,
    CONF_VALUE,
    CONF_VARIANCE,
    DEFAULT_VARIANCE,
    ATTR_INTEGRATION_METHOD,
    ATTR_LAST_CALC_TIME,
    ATTR_MEMBER_COUNT,
    ATTR_MEMBERS,
    ATTR_MIN_POWER,
    ATTR_POWER_SENSOR,
    ATTR_RATED_POWER,
    ATTR_SOURCE_ENTITY,
    ATTR_STANDBY_POWER,
    COMPONENT_DOMAIN,
    CONF_ENERGY_SENSORS,
    CONF_ENTITIES,
    CONF_GROUP_SENSORS,
    CONF_INITIAL_VALUE,
    CONF_INTEGRATION_METHOD,
    CONF_LINK_DEVICE,
    CONF_MIN_POWER,
    CONF_POWER,
    CONF_POWER_SENSOR,
    CONF_POWER_SENSORS,
    CONF_STANDBY_POWER,
    DEFAULT_INITIAL_VALUE,
    DEFAULT_INTEGRATION_METHOD,
    DEFAULT_LINK_DEVICE,
    DEFAULT_MIN_POWER,
    DEFAULT_STANDBY_POWER,
    DEFAULT_TICK_INTERVAL_SECONDS,
    INTEGRATION_METHOD_LEFT,
    SERVICE_RESET_ENERGY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: entity_platform.AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Phantom Power sensors from platform configuration."""
    if not discovery_info:
        return

    entities: list[SensorEntity] = []

    for p_cfg in discovery_info.get(CONF_POWER_SENSORS, []):
        entities.append(PhantomPowerSensor(p_cfg))

    for g_cfg in discovery_info.get(CONF_GROUP_SENSORS, []):
        entities.append(PhantomPowerGroupSensor(g_cfg))

    for e_cfg in discovery_info.get(CONF_ENERGY_SENSORS, []):
        entities.append(PhantomEnergySensor(e_cfg))

    if entities:
        async_add_entities(entities)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up Phantom Power sensors from a config entry."""
    data = hass.data.get(COMPONENT_DOMAIN, {}).get(entry.entry_id, {})
    cfg = data.get("config", {})

    entities: list[SensorEntity] = []

    for p_cfg in cfg.get(CONF_POWER_SENSORS, []):
        entities.append(PhantomPowerSensor(p_cfg))

    for g_cfg in cfg.get(CONF_GROUP_SENSORS, []):
        entities.append(PhantomPowerGroupSensor(g_cfg))

    for e_cfg in cfg.get(CONF_ENERGY_SENSORS, []):
        entities.append(PhantomEnergySensor(e_cfg))

    if entities:
        async_add_entities(entities)


class PhantomPowerSensor(RestoreEntity, SensorEntity):
    """Calculates power consumption based on a target entity state and level."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 2
    _attr_has_entity_name = False

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the Phantom Power sensor."""
        self._config = config
        self._attr_name = config[CONF_NAME]
        self._source_entity_id = config[CONF_ENTITY_ID]
        self._power = float(config[CONF_POWER])
        self._min_power = float(config.get(CONF_MIN_POWER, DEFAULT_MIN_POWER))
        self._standby_power = float(config.get(CONF_STANDBY_POWER, DEFAULT_STANDBY_POWER))
        self._link_device = config.get(CONF_LINK_DEVICE, DEFAULT_LINK_DEVICE)
        self._states = list(config.get(CONF_STATES, []))
        self._variance = float(config.get(CONF_VARIANCE, DEFAULT_VARIANCE))
        self._active_rule: str | None = None

        self._attr_unique_id = config.get("unique_id") or f"phantom_power_{slugify(self._attr_name)}"
        self.entity_id = f"sensor.{slugify(self._attr_name)}"

        self._attr_extra_state_attributes = {
            ATTR_SOURCE_ENTITY: self._source_entity_id,
            ATTR_RATED_POWER: self._power,
            ATTR_MIN_POWER: self._min_power,
            ATTR_STANDBY_POWER: self._standby_power,
        }
        self._unsub_track: Any = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to Home Assistant."""
        await super().async_added_to_hass()

        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            try:
                self._attr_native_value = float(last_state.state)
            except (ValueError, TypeError):
                self._attr_native_value = self._standby_power

        # Link to target device if requested
        if self._link_device:
            self._async_link_to_source_device()

        @callback
        def _async_on_source_change(event: Event) -> None:
            new_state = event.data.get("new_state")
            self._update_from_source(new_state)

        self._unsub_track = async_track_state_change_event(
            self.hass, [self._source_entity_id], _async_on_source_change
        )

        # Evaluate current state immediately
        current_state = self.hass.states.get(self._source_entity_id)
        self._update_from_source(current_state)

    @callback
    def _async_link_to_source_device(self) -> None:
        """Link this power sensor to the device of the source entity."""
        try:
            ent_reg = er.async_get(self.hass)
            source_entry = ent_reg.async_get(self._source_entity_id)
            if source_entry and source_entry.device_id:
                my_entry = ent_reg.async_get(self.entity_id)
                if my_entry and my_entry.device_id != source_entry.device_id:
                    _LOGGER.debug(
                        "Linking power sensor %s to device %s of source %s",
                        self.entity_id,
                        source_entry.device_id,
                        self._source_entity_id,
                    )
                    ent_reg.async_update_entity(
                        self.entity_id, device_id=source_entry.device_id
                    )
        except Exception as err:
            _LOGGER.debug("Could not link device for %s: %s", self.entity_id, err)

    @callback
    def _update_from_source(self, state: Any) -> None:
        """Recalculate power draw based on current source entity state."""
        if self._states:
            wattage = self._standby_power
            self._active_rule = "standby"
            if state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                for rule in self._states:
                    if CONF_ATTRIBUTE in rule:
                        attr_val = state.attributes.get(rule[CONF_ATTRIBUTE])
                    else:
                        attr_val = state.state

                    if attr_val is None:
                        continue

                    matched = False
                    if CONF_CONTAINS in rule:
                        needle = str(rule[CONF_CONTAINS]).strip().lower()
                        if isinstance(attr_val, (list, tuple, set)):
                            matched = any(needle in str(x).lower() for x in attr_val)
                        else:
                            matched = needle in str(attr_val).lower()
                    elif CONF_VALUE in rule:
                        matched = str(attr_val).strip().lower() == str(rule[CONF_VALUE]).strip().lower()
                    elif CONF_STATE in rule:
                        matched = str(state.state).strip().lower() == str(rule[CONF_STATE]).strip().lower()

                    if matched:
                        try:
                            wattage = float(rule[CONF_POWER])
                        except (ValueError, TypeError):
                            wattage = self._standby_power

                        desc_target = rule.get(CONF_ATTRIBUTE, "state")
                        if CONF_CONTAINS in rule:
                            self._active_rule = f"{desc_target}~={rule[CONF_CONTAINS]}"
                        else:
                            self._active_rule = f"{desc_target}=={rule.get(CONF_VALUE, rule.get(CONF_STATE))}"
                        break
        else:
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                wattage = self._standby_power
            elif state.state == STATE_ON:
                # Check for dimmer / brightness (0..255)
                brightness = state.attributes.get("brightness")
                percentage = state.attributes.get("percentage")

                if brightness is not None:
                    try:
                        fraction = max(0.0, min(1.0, float(brightness) / 255.0))
                        wattage = self._min_power + fraction * (self._power - self._min_power)
                    except (ValueError, TypeError):
                        wattage = self._power
                elif percentage is not None:
                    try:
                        fraction = max(0.0, min(1.0, float(percentage) / 100.0))
                        wattage = self._min_power + fraction * (self._power - self._min_power)
                    except (ValueError, TypeError):
                        wattage = self._power
                else:
                    wattage = self._power
            elif state.state == STATE_OFF:
                wattage = self._standby_power
            else:
                # Handle non-binary states (e.g. media player playing/idle/paused)
                st_lower = str(state.state).lower()
                if st_lower in ("playing", "active", "open"):
                    wattage = self._power
                elif st_lower in ("standby", "idle", "paused"):
                    wattage = self._standby_power
                else:
                    wattage = self._standby_power

        # Apply realistic variance/jitter if configured and active
        if self._variance > 0.0 and wattage > 0.0:
            wattage = max(0.0, wattage + random.uniform(-self._variance, self._variance))

        self._attr_native_value = round(max(0.0, float(wattage)), 2)
        self._attr_extra_state_attributes.update(
            {
                ATTR_SOURCE_ENTITY: self._source_entity_id,
                ATTR_RATED_POWER: self._power,
                ATTR_MIN_POWER: self._min_power,
                ATTR_STANDBY_POWER: self._standby_power,
                ATTR_VARIANCE: self._variance,
            }
        )
        if self._states:
            self._attr_extra_state_attributes[ATTR_ACTIVE_RULE] = self._active_rule
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up state listener on removal."""
        if self._unsub_track:
            self._unsub_track()
            self._unsub_track = None
        if self.hass and COMPONENT_DOMAIN in self.hass.data:
            self.hass.data[COMPONENT_DOMAIN].get("energy_sensors", {}).pop(self.entity_id, None)
        await super().async_will_remove_from_hass()


class PhantomEnergySensor(RestoreEntity, SensorEntity):
    """Integrates a power sensor into cumulative kWh."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3
    _attr_has_entity_name = False

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the Phantom Energy sensor."""
        self._config = config
        self._attr_name = config[CONF_NAME]
        self._source_power_sensor = config[CONF_POWER_SENSOR]
        self._integration_method = config.get(
            CONF_INTEGRATION_METHOD, DEFAULT_INTEGRATION_METHOD
        )

        self._energy_accumulator = float(
            config.get(CONF_INITIAL_VALUE, DEFAULT_INITIAL_VALUE)
        )
        self._last_calc_time: datetime.datetime | None = None
        self._last_power: float = 0.0

        self._attr_unique_id = config.get("unique_id") or f"phantom_energy_{slugify(self._attr_name)}"
        self.entity_id = f"sensor.{slugify(self._attr_name)}"

        self._attr_extra_state_attributes = {
            ATTR_POWER_SENSOR: self._source_power_sensor,
            ATTR_INTEGRATION_METHOD: self._integration_method,
        }

        self._unsub_power: Any = None
        self._unsub_interval: Any = None

    async def async_added_to_hass(self) -> None:
        """Restore state and start power tracking & interval accumulation."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            try:
                self._energy_accumulator = float(last_state.state)
            except (ValueError, TypeError):
                pass

        self._attr_native_value = round(self._energy_accumulator, 4)

        # Read initial power level
        st = self.hass.states.get(self._source_power_sensor)
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            try:
                self._last_power = max(0.0, float(st.state))
            except (ValueError, TypeError):
                self._last_power = 0.0

        self._last_calc_time = dt_util.utcnow()

        @callback
        def _on_power_state_change(event: Event) -> None:
            new_st = event.data.get("new_state")
            if new_st is None or new_st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return
            try:
                new_power = max(0.0, float(new_st.state))
                self._accumulate_energy(new_power)
            except (ValueError, TypeError):
                pass

        self._unsub_power = async_track_state_change_event(
            self.hass, [self._source_power_sensor], _on_power_state_change
        )

        # Register in energy sensor registry for reset service
        self.hass.data.setdefault(COMPONENT_DOMAIN, {}).setdefault("energy_sensors", {})[self.entity_id] = self

        self._unsub_interval = async_track_time_interval(
            self.hass,
            self._on_interval_tick,
            datetime.timedelta(seconds=DEFAULT_TICK_INTERVAL_SECONDS),
        )

    @callback
    def _on_interval_tick(self, _now: datetime.datetime) -> None:
        """Periodic tick to ensure steady energy accumulation."""
        self._accumulate_energy()

    @callback
    def _accumulate_energy(self, new_power: float | None = None) -> None:
        """Integrate power over elapsed seconds into cumulative kWh."""
        now = dt_util.utcnow()
        if self._last_calc_time is None:
            self._last_calc_time = now
            if new_power is not None:
                self._last_power = new_power
            return

        elapsed_seconds = (now - self._last_calc_time).total_seconds()
        if elapsed_seconds <= 0:
            if new_power is not None:
                self._last_power = new_power
            return

        # Check unit of power sensor (convert kW to W if needed)
        st = self.hass.states.get(self._source_power_sensor)
        unit = st.attributes.get(ATTR_UNIT_OF_MEASUREMENT, "W") if st else "W"
        is_kw = str(unit).strip().lower() in ("kw", "kilowatt")

        curr_p = (new_power if new_power is not None else self._last_power)
        if is_kw:
            curr_p_watts = curr_p * 1000.0
            last_p_watts = self._last_power * 1000.0
        else:
            curr_p_watts = curr_p
            last_p_watts = self._last_power

        # Apply integration method
        if self._integration_method == INTEGRATION_METHOD_LEFT:
            avg_watts = last_p_watts
        else:
            # Default trapezoidal
            avg_watts = (last_p_watts + curr_p_watts) / 2.0

        # Energy in kWh: (Watts * seconds) / (3600 seconds/hr * 1000 W/kW)
        added_kwh = (avg_watts * elapsed_seconds) / 3600000.0
        self._energy_accumulator += max(0.0, added_kwh)

        self._last_calc_time = now
        if new_power is not None:
            self._last_power = new_power

        self._attr_native_value = round(self._energy_accumulator, 4)
        self._attr_extra_state_attributes[ATTR_LAST_CALC_TIME] = now.isoformat()
        self.async_write_ha_state()

    @callback
    def async_reset_energy(self, value: float = 0.0) -> None:
        """Reset the accumulated energy to a specific value."""
        self._energy_accumulator = max(0.0, float(value))
        self._last_calc_time = dt_util.utcnow()
        self._attr_native_value = round(self._energy_accumulator, 4)
        _LOGGER.info("Reset %s accumulated energy to %s kWh", self.entity_id, value)
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up timers and subscriptions."""
        if self._unsub_power:
            self._unsub_power()
            self._unsub_power = None
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None
        await super().async_will_remove_from_hass()


class PhantomPowerGroupSensor(RestoreEntity, SensorEntity):
    """Aggregates multiple power sensors into a total wattage reading."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 2
    _attr_has_entity_name = False

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the Phantom Power Group sensor."""
        self._config = config
        self._attr_name = config[CONF_NAME]
        self._entities: list[str] = list(config[CONF_ENTITIES])

        self._attr_unique_id = config.get("unique_id") or f"phantom_group_{slugify(self._attr_name)}"
        self.entity_id = f"sensor.{slugify(self._attr_name)}"

        self._attr_extra_state_attributes = {
            ATTR_MEMBERS: {},
            ATTR_MEMBER_COUNT: len(self._entities),
            ATTR_ACTIVE_MEMBERS: 0,
        }
        self._unsub_track: Any = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to member state changes and perform initial sum."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            try:
                self._attr_native_value = float(last_state.state)
            except (ValueError, TypeError):
                pass

        @callback
        def _on_member_state_change(_event: Event) -> None:
            self._recalculate_group_power()

        self._unsub_track = async_track_state_change_event(
            self.hass, self._entities, _on_member_state_change
        )

        self._recalculate_group_power()

    @callback
    def _recalculate_group_power(self) -> None:
        """Sum power from all member entities."""
        member_powers: dict[str, float] = {}
        total_watts = 0.0

        for ent_id in self._entities:
            st = self.hass.states.get(ent_id)
            if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
                try:
                    val = float(st.state)
                    # Convert kW to W if member reports kW
                    unit = st.attributes.get(ATTR_UNIT_OF_MEASUREMENT, "W")
                    if str(unit).strip().lower() in ("kw", "kilowatt"):
                        val *= 1000.0
                    val = max(0.0, val)
                except (ValueError, TypeError):
                    val = 0.0
            else:
                val = 0.0

            member_powers[ent_id] = round(val, 2)
            total_watts += val

        active_count = sum(1 for p in member_powers.values() if p > 0.0)

        self._attr_native_value = round(total_watts, 2)
        self._attr_extra_state_attributes = {
            ATTR_MEMBERS: member_powers,
            ATTR_MEMBER_COUNT: len(self._entities),
            ATTR_ACTIVE_MEMBERS: active_count,
        }
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up tracking subscription."""
        if self._unsub_track:
            self._unsub_track()
            self._unsub_track = None
        await super().async_will_remove_from_hass()
