"""Configuration handling and schema validation for Phantom Power."""
from __future__ import annotations

import logging
import os
from typing import Any
import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_UNIQUE_ID,
    CONF_ENTITY_ID,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.util.yaml import parse_yaml

from .const import (
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
    CONF_ATTRIBUTE,
    CONF_CONTAINS,
    CONF_STATE,
    CONF_STATES,
    CONF_VALUE,
    CONF_VARIANCE,
    DEFAULT_VARIANCE,
    DEFAULT_INITIAL_VALUE,
    DEFAULT_INTEGRATION_METHOD,
    DEFAULT_LINK_DEVICE,
    DEFAULT_MIN_POWER,
    DEFAULT_POWER,
    DEFAULT_STANDBY_POWER,
    INTEGRATION_METHOD_LEFT,
    INTEGRATION_METHOD_TRAPEZOIDAL,
    default_config_file,
)

_LOGGER = logging.getLogger(__name__)

STATE_RULE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ATTRIBUTE): cv.string,
        vol.Optional(CONF_VALUE): cv.match_all,
        vol.Optional(CONF_CONTAINS): cv.string,
        vol.Optional(CONF_STATE): cv.string,
        vol.Required(CONF_POWER): vol.Coerce(float),
    }
)

POWER_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Optional(CONF_POWER, default=DEFAULT_POWER): vol.Coerce(float),
        vol.Optional(CONF_MIN_POWER, default=DEFAULT_MIN_POWER): vol.Coerce(float),
        vol.Optional(CONF_STANDBY_POWER, default=DEFAULT_STANDBY_POWER): vol.Coerce(float),
        vol.Optional(CONF_VARIANCE, default=DEFAULT_VARIANCE): vol.Coerce(float),
        vol.Optional(CONF_LINK_DEVICE, default=DEFAULT_LINK_DEVICE): cv.boolean,
        vol.Optional(CONF_STATES, default=[]): vol.All(
            cv.ensure_list, [STATE_RULE_SCHEMA]
        ),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

GROUP_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_ENTITIES): cv.entity_ids,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

ENERGY_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_POWER_SENSOR): cv.entity_id,
        vol.Optional(CONF_INITIAL_VALUE, default=DEFAULT_INITIAL_VALUE): vol.Coerce(float),
        vol.Optional(
            CONF_INTEGRATION_METHOD, default=DEFAULT_INTEGRATION_METHOD
        ): vol.In([INTEGRATION_METHOD_TRAPEZOIDAL, INTEGRATION_METHOD_LEFT]),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

PHANTOM_POWER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_POWER_SENSORS, default=[]): vol.All(
            cv.ensure_list, [POWER_SENSOR_SCHEMA]
        ),
        vol.Optional(CONF_GROUP_SENSORS, default=[]): vol.All(
            cv.ensure_list, [GROUP_SENSOR_SCHEMA]
        ),
        vol.Optional(CONF_ENERGY_SENSORS, default=[]): vol.All(
            cv.ensure_list, [ENERGY_SENSOR_SCHEMA]
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(COMPONENT_DOMAIN): PHANTOM_POWER_SCHEMA,
    },
    extra=vol.ALLOW_EXTRA,
)


def _read_file(file_name: str) -> str:
    with open(file_name, "r", encoding="utf-8") as f:
        return f.read()


async def async_load_phantom_config(
    hass: HomeAssistant, file_path: str | None = None
) -> dict[str, Any]:
    """Load and validate the Phantom Power YAML configuration."""
    target_path = file_path or default_config_file(hass)
    _LOGGER.debug("Loading Phantom Power configuration from %s", target_path)

    if not os.path.exists(target_path):
        _LOGGER.info(
            "Phantom Power config file %s does not exist; using empty configuration",
            target_path,
        )
        return {
            CONF_POWER_SENSORS: [],
            CONF_GROUP_SENSORS: [],
            CONF_ENERGY_SENSORS: [],
        }

    try:
        content = await hass.async_add_executor_job(_read_file, target_path)
        raw_yaml = parse_yaml(content)
        if not raw_yaml:
            return {
                CONF_POWER_SENSORS: [],
                CONF_GROUP_SENSORS: [],
                CONF_ENERGY_SENSORS: [],
            }

        # If file has root 'phantom_power:' key, unwrap it
        if isinstance(raw_yaml, dict) and COMPONENT_DOMAIN in raw_yaml:
            raw_yaml = raw_yaml[COMPONENT_DOMAIN]

        validated = PHANTOM_POWER_SCHEMA(raw_yaml)
        return validated
    except Exception as err:
        _LOGGER.error("Failed to load Phantom Power configuration from %s: %s", target_path, err)
        return {
            CONF_POWER_SENSORS: [],
            CONF_GROUP_SENSORS: [],
            CONF_ENERGY_SENSORS: [],
        }
