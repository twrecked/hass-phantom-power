"""Config flow for Phantom Power."""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any
from urllib.parse import quote
import zlib
try:
    import probatio as vol
except ImportError:
    import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    COMPONENT_DOMAIN,
    COMPONENT_NAME,
    CONF_EDITOR_URL,
    CONF_FILE_NAME,
    DEFAULT_EDITOR_URL,
    default_config_file,
)

_LOGGER = logging.getLogger(__name__)


class PhantomPowerFlowHandler(config_entries.ConfigFlow, domain=COMPONENT_DOMAIN):
    """Handle a config flow for Phantom Power."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return PhantomPowerOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(COMPONENT_DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=COMPONENT_NAME,
                data={
                    CONF_FILE_NAME: user_input.get(
                        CONF_FILE_NAME, default_config_file(self.hass)
                    ),
                    CONF_EDITOR_URL: user_input.get(
                        CONF_EDITOR_URL, DEFAULT_EDITOR_URL
                    ),
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_FILE_NAME, default=default_config_file(self.hass)
                ): cv.string,
                vol.Optional(
                    CONF_EDITOR_URL, default=DEFAULT_EDITOR_URL
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle import from configuration.yaml."""
        await self.async_set_unique_id(COMPONENT_DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=COMPONENT_NAME,
            data={
                CONF_FILE_NAME: (user_input or {}).get(
                    CONF_FILE_NAME, default_config_file(self.hass)
                ),
                CONF_EDITOR_URL: (user_input or {}).get(
                    CONF_EDITOR_URL, DEFAULT_EDITOR_URL
                ),
            },
        )


class PhantomPowerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Phantom Power options and editor launching."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options and present the editor launch URL."""
        entry = self.config_entry

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        file_name = entry.options.get(
            CONF_FILE_NAME, entry.data.get(CONF_FILE_NAME, default_config_file(self.hass))
        )
        editor_url = entry.options.get(
            CONF_EDITOR_URL, entry.data.get(CONF_EDITOR_URL, DEFAULT_EDITOR_URL)
        )

        # 1. Read existing YAML file safely
        def _read() -> str:
            if os.path.exists(file_name):
                with open(file_name, "r", encoding="utf-8") as f:
                    return f.read()
            return ""

        try:
            yaml_content = await self.hass.async_add_executor_job(_read)
        except Exception as err:
            _LOGGER.debug("Could not read %s: %s", file_name, err)
            yaml_content = ""

        # 2. Collect candidate entities from Home Assistant state machine
        candidate_entities: list[dict[str, Any]] = []
        for state in self.hass.states.async_all():
            domain = state.domain
            if domain in ("light", "switch", "fan", "media_player", "climate", "vacuum"):
                # Collect relevant attribute keys
                attrs = [k for k in state.attributes.keys() if k not in ("friendly_name", "icon", "supported_features", "entity_picture")]
                candidate_entities.append(
                    {
                        "entity_id": state.entity_id,
                        "name": state.attributes.get("friendly_name", state.entity_id),
                        "domain": domain,
                        "is_dimmable": domain == "light"
                        or (domain == "fan" and "percentage" in state.attributes),
                        "attributes": attrs,
                    }
                )
        candidate_entities.sort(key=lambda x: (x["domain"], x["name"].lower()))

        # 3. Build payload and encode
        payload = json.dumps(
            {
                "yaml": yaml_content,
                "entities": candidate_entities,
            }
        )
        compressed = zlib.compress(payload.encode("utf-8"))
        encoded_data = base64.b64encode(compressed).decode("ascii")

        # 4. Webhook callback information
        webhook_id = f"{COMPONENT_DOMAIN}_{entry.entry_id}"
        token = (
            self.hass.data.get(f"{COMPONENT_DOMAIN}_webhooks", {})
            .get(entry.entry_id, {})
            .get("webhook_token", "")
        )

        try:
            webhook_url = webhook.async_generate_url(
                self.hass, webhook_id, allow_internal=True, allow_external=True
            )
        except Exception:
            webhook_url = f"/api/webhook/{webhook_id}"

        cb_param = (
            f"{webhook_url}?token={token}"
            if "?" not in webhook_url
            else f"{webhook_url}&token={token}"
        )

        builder_url = (
            f"{editor_url}/?cb={quote(cb_param, safe='')}"
            f"&token={quote(token)}"
            f"&name={quote(os.path.basename(file_name))}"
            f"#data={encoded_data}"
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_FILE_NAME, default=file_name): cv.string,
                vol.Required(CONF_EDITOR_URL, default=editor_url): cv.string,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "builder_url": builder_url,
                "file_name": file_name,
            },
        )
