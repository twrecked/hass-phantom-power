"""The Phantom Power integration."""
from __future__ import annotations

import logging
import secrets
from typing import Any
from aiohttp import web
try:
    import probatio as vol
except ImportError:
    import voluptuous as vol
import yaml

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import ATTR_ENTITY_ID, CONF_SOURCE, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .cfg import CONFIG_SCHEMA, async_load_phantom_config
from .const import (
    COMPONENT_DOMAIN,
    CONF_ENERGY_SENSORS,
    CONF_FILE_NAME,
    CONF_GROUP_SENSORS,
    CONF_POWER_SENSORS,
    SERVICE_RELOAD,
    SERVICE_RESET_ENERGY,
    default_config_file,
)

__version__ = "0.1.0-alpha.1"

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_RESET_ENERGY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
        vol.Optional("value", default=0.0): vol.Coerce(float),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Phantom Power component from configuration.yaml."""
    hass.data.setdefault(COMPONENT_DOMAIN, {})
    hass.data[COMPONENT_DOMAIN].setdefault("energy_sensors", {})

    if COMPONENT_DOMAIN in config:
        hass.data[COMPONENT_DOMAIN]["yaml_raw"] = config[COMPONENT_DOMAIN]
        # Auto-import into config entries if not already present
        if not hass.config_entries.async_entries(COMPONENT_DOMAIN):
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    COMPONENT_DOMAIN,
                    context={CONF_SOURCE: SOURCE_IMPORT},
                    data={CONF_FILE_NAME: default_config_file(hass)},
                )
            )

    # Register integration-level services
    async def async_handle_reload(_call: ServiceCall) -> None:
        """Reload configuration from disk across all entries."""
        _LOGGER.info("Reloading Phantom Power integration")
        for entry in hass.config_entries.async_entries(COMPONENT_DOMAIN):
            await hass.config_entries.async_reload(entry.entry_id)

    async def async_handle_reset_energy(call: ServiceCall) -> None:
        """Reset accumulated energy on target sensors."""
        target_ids = call.data[ATTR_ENTITY_ID]
        if isinstance(target_ids, str):
            target_ids = [target_ids]
        reset_val = call.data.get("value", 0.0)

        registry = hass.data.get(COMPONENT_DOMAIN, {}).get("energy_sensors", {})
        for ent_id in target_ids:
            sensor = registry.get(ent_id)
            if sensor and hasattr(sensor, "async_reset_energy"):
                sensor.async_reset_energy(reset_val)
            else:
                _LOGGER.warning(
                    "Entity %s is not a recognized active Phantom Energy sensor",
                    ent_id,
                )

    hass.services.async_register(
        COMPONENT_DOMAIN, SERVICE_RELOAD, async_handle_reload
    )
    hass.services.async_register(
        COMPONENT_DOMAIN,
        SERVICE_RESET_ENERGY,
        async_handle_reset_energy,
        schema=SERVICE_RESET_ENERGY_SCHEMA,
    )

    return True


async def _async_handle_editor_webhook(
    hass: HomeAssistant, webhook_id: str, request: web.Request, entry: ConfigEntry
) -> web.Response:
    """Handle incoming YAML save from Phantom Power Editor."""
    token = request.query.get("token") or request.headers.get("X-Auth-Token")
    expected_token = (
        hass.data.get(f"{COMPONENT_DOMAIN}_webhooks", {})
        .get(entry.entry_id, {})
        .get("webhook_token")
    )
    if not token or token != expected_token:
        _LOGGER.warning("Invalid token received on Phantom Power editor webhook")
        return web.Response(text="Invalid token", status=403)

    body = await request.text()
    if not body:
        return web.Response(text="Empty body", status=400)

    try:
        parsed = yaml.safe_load(body)
        if not isinstance(parsed, dict):
            return web.Response(text="YAML root must be a dictionary", status=400)
    except Exception as err:
        _LOGGER.warning("Invalid YAML received on editor webhook: %s", err)
        return web.Response(text=f"Invalid YAML: {err}", status=400)

    file_name = entry.options.get(
        CONF_FILE_NAME, entry.data.get(CONF_FILE_NAME, default_config_file(hass))
    )

    def _write_yaml() -> None:
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(body)

    await hass.async_add_executor_job(_write_yaml)
    _LOGGER.info("Successfully updated %s from Phantom Power Editor", file_name)

    # Reload config entry asynchronously to pick up changes
    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))
    return web.Response(text="OK", status=200)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Phantom Power from a config entry."""
    hass.data.setdefault(COMPONENT_DOMAIN, {})
    hass.data[COMPONENT_DOMAIN].setdefault("energy_sensors", {})

    file_name = entry.options.get(
        CONF_FILE_NAME, entry.data.get(CONF_FILE_NAME, default_config_file(hass))
    )

    loaded_cfg = await async_load_phantom_config(hass, file_name)

    # Merge configuration.yaml data if present
    yaml_raw = hass.data[COMPONENT_DOMAIN].get("yaml_raw", {})
    if yaml_raw:
        for section in (CONF_POWER_SENSORS, CONF_GROUP_SENSORS, CONF_ENERGY_SENSORS):
            existing = loaded_cfg.get(section, [])
            from_yaml = yaml_raw.get(section, [])
            existing_names = {x.get("name") for x in existing if isinstance(x, dict)}
            for item in from_yaml:
                if isinstance(item, dict) and item.get("name") not in existing_names:
                    existing.append(item)
            loaded_cfg[section] = existing

    hass.data[COMPONENT_DOMAIN][entry.entry_id] = {
        "config": loaded_cfg,
        "file_name": file_name,
    }

    # Register editor webhook
    webhook_id = f"{COMPONENT_DOMAIN}_{entry.entry_id}"
    token = secrets.token_hex(16)
    webhooks_data = hass.data.setdefault(f"{COMPONENT_DOMAIN}_webhooks", {})
    webhooks_data[entry.entry_id] = {
        "webhook_token": token,
        "webhook_id": webhook_id,
    }

    async def _handle_webhook(
        hass_inst: HomeAssistant, wh_id: str, req: web.Request
    ) -> web.Response:
        return await _async_handle_editor_webhook(hass_inst, wh_id, req, entry)

    try:
        webhook.async_register(
            hass,
            COMPONENT_DOMAIN,
            "Phantom Power Editor",
            webhook_id,
            _handle_webhook,
        )
    except Exception as err:
        _LOGGER.debug("Webhook registration skipped: %s", err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Phantom Power config entry."""
    webhook_id = f"{COMPONENT_DOMAIN}_{entry.entry_id}"
    try:
        webhook.async_unregister(hass, webhook_id)
    except Exception:
        pass
    hass.data.get(f"{COMPONENT_DOMAIN}_webhooks", {}).pop(entry.entry_id, None)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[COMPONENT_DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)
