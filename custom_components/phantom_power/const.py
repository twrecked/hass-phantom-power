"""Constants for the Phantom Power component."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

COMPONENT_DOMAIN = "phantom_power"
COMPONENT_NAME = "Phantom Power"
COMPONENT_MANUFACTURER = "twrecked"
COMPONENT_MODEL = "phantom_power"

# Configuration sections
CONF_POWER_SENSORS = "power_sensors"
CONF_GROUP_SENSORS = "group_sensors"
CONF_ENERGY_SENSORS = "energy_sensors"

# Entity configuration keys
CONF_POWER = "power"
CONF_STATES = "states"
CONF_ATTRIBUTE = "attribute"
CONF_VALUE = "value"
CONF_CONTAINS = "contains"
CONF_STATE = "state"
CONF_VARIANCE = "variance"
DEFAULT_VARIANCE = 0.0

ATTR_VARIANCE = "variance"
ATTR_ACTIVE_RULE = "active_rule"
CONF_MIN_POWER = "min_power"
CONF_STANDBY_POWER = "standby_power"
CONF_LINK_DEVICE = "link_device"
CONF_POWER_SENSOR = "power_sensor"
CONF_INTEGRATION_METHOD = "integration_method"
CONF_INITIAL_VALUE = "initial_value"
CONF_ENTITIES = "entities"
CONF_UNIQUE_ID = "unique_id"
ATTR_UNIQUE_ID = "unique_id"
CONF_FILE_NAME = "file_name"
CONF_EDITOR_URL = "editor_url"
DEFAULT_EDITOR_URL = "https://phantom-power-dot-twrecked-tools.nn.r.appspot.com"

# Integration methods
INTEGRATION_METHOD_TRAPEZOIDAL = "trapezoidal"
INTEGRATION_METHOD_LEFT = "left"

# Defaults
DEFAULT_CONFIG_FILE = "phantom_power.yaml"
DEFAULT_POWER = 0.0
DEFAULT_STANDBY_POWER = 0.0
DEFAULT_MIN_POWER = 0.0
DEFAULT_LINK_DEVICE = True
DEFAULT_INTEGRATION_METHOD = INTEGRATION_METHOD_TRAPEZOIDAL
DEFAULT_INITIAL_VALUE = 0.0
DEFAULT_TICK_INTERVAL_SECONDS = 30

# Services
SERVICE_RELOAD = "reload"
SERVICE_RESET_ENERGY = "reset_energy"

# Extra state attributes
ATTR_SOURCE_ENTITY = "source_entity"
ATTR_RATED_POWER = "rated_power"
ATTR_STANDBY_POWER = "standby_power"
ATTR_MIN_POWER = "min_power"
ATTR_POWER_SENSOR = "power_sensor"
ATTR_INTEGRATION_METHOD = "integration_method"
ATTR_MEMBERS = "members"
ATTR_MEMBER_COUNT = "member_count"
ATTR_ACTIVE_MEMBERS = "active_members"
ATTR_LAST_CALC_TIME = "last_calc_time"


def default_config_file(hass: HomeAssistant) -> str:
    """Return default configuration file path."""
    return os.path.join(hass.config.config_dir, DEFAULT_CONFIG_FILE)
