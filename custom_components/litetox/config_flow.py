"""Config, reconfigure, reauth and options flows for Litetox Proxy."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_API_TOKEN, CONF_NAME, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import LitetoxAuthError, LitetoxClient, LitetoxError
from .const import (
    CONF_ALTOX_HOST,
    CONF_ALTOX_PORT,
    CONF_HEATER_MINUTES,
    CONF_IMEI,
    CONF_SCAN_INTERVAL,
    DEFAULT_ALTOX_HOST,
    DEFAULT_ALTOX_PORT,
    DEFAULT_HEATER_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_IMEI_RE = re.compile(r"^[0-9A-Za-z_-]{4,32}$")
_HOST_RE = re.compile(r"^[0-9A-Za-z.-]{1,253}$")
_URL = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))
_TOKEN = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


async def _check(hass, url: str, token: str) -> dict[str, str]:
    """Token is verified by an authenticated call (/health is public)."""
    client = LitetoxClient(async_get_clientsession(hass), url, token)
    try:
        await client.devices()
    except LitetoxAuthError:
        return {"base": "invalid_auth"}
    except LitetoxError:
        return {"base": "cannot_connect"}
    return {}


class LitetoxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Server URL + token + tracker IMEI; registers the IMEI on the server."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            imei = user_input[CONF_IMEI].strip()
            name = user_input[CONF_NAME].strip() or imei
            if not _IMEI_RE.match(imei):
                errors[CONF_IMEI] = "invalid_imei"
            else:
                await self.async_set_unique_id(imei)
                self._abort_if_unique_id_configured()
                errors = await _check(self.hass, url, user_input[CONF_API_TOKEN])
                if not errors:
                    client = LitetoxClient(
                        async_get_clientsession(self.hass), url, user_input[CONF_API_TOKEN]
                    )
                    try:
                        await client.register(imei, name)
                    except LitetoxError:
                        errors["base"] = "register_failed"
                if not errors:
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_URL: url,
                            CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                            CONF_IMEI: imei,
                            CONF_NAME: name,
                        },
                    )
        schema = vol.Schema(
            {
                vol.Required(CONF_URL): _URL,
                vol.Required(CONF_API_TOKEN): _TOKEN,
                vol.Required(CONF_IMEI): str,
                vol.Required(CONF_NAME): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change server URL / token (IMEI stays — it is the entry identity)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            errors = await _check(self.hass, url, user_input[CONF_API_TOKEN])
            if not errors:
                client = LitetoxClient(
                    async_get_clientsession(self.hass), url, user_input[CONF_API_TOKEN]
                )
                try:
                    await client.register(entry.data[CONF_IMEI], entry.data[CONF_NAME])
                except LitetoxError:
                    errors["base"] = "register_failed"
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_URL: url, CONF_API_TOKEN: user_input[CONF_API_TOKEN]}
                )
        schema = vol.Schema({vol.Required(CONF_URL): _URL, vol.Required(CONF_API_TOKEN): _TOKEN})
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or {CONF_URL: entry.data[CONF_URL]}
            ),
            description_placeholders={"imei": entry.data[CONF_IMEI]},
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _check(self.hass, entry.data[CONF_URL], user_input[CONF_API_TOKEN])
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_TOKEN: user_input[CONF_API_TOKEN]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): _TOKEN}),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return LitetoxOptionsFlow()


class LitetoxOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = (user_input.get(CONF_ALTOX_HOST) or "").strip()
            port = int(user_input[CONF_ALTOX_PORT])
            if host and not _HOST_RE.match(host):
                errors[CONF_ALTOX_HOST] = "invalid_host"
            else:
                # the proxy keeps the ALTOX server per IMEI; empty host = mirror off
                entry = self.config_entry
                client = LitetoxClient(
                    async_get_clientsession(self.hass),
                    entry.data[CONF_URL],
                    entry.data[CONF_API_TOKEN],
                )
                try:
                    await client.register(
                        entry.data[CONF_IMEI],
                        entry.data[CONF_NAME],
                        f"{host}:{port}" if host else "",
                    )
                except LitetoxAuthError:
                    errors["base"] = "invalid_auth"
                except LitetoxError:
                    errors["base"] = "cannot_connect"
            if not errors:
                return self.async_create_entry(
                    data={
                        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                        CONF_HEATER_MINUTES: int(user_input[CONF_HEATER_MINUTES]),
                        CONF_ALTOX_HOST: host,
                        CONF_ALTOX_PORT: port,
                    }
                )
        opts = {**self.config_entry.options, **(user_input or {})}
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_HEATER_MINUTES,
                        default=opts.get(CONF_HEATER_MINUTES, DEFAULT_HEATER_MINUTES),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=120, step=5, unit_of_measurement="min",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_ALTOX_HOST,
                        description={
                            "suggested_value": opts.get(CONF_ALTOX_HOST, DEFAULT_ALTOX_HOST)
                        },
                    ): str,
                    vol.Required(
                        CONF_ALTOX_PORT,
                        default=opts.get(CONF_ALTOX_PORT, DEFAULT_ALTOX_PORT),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=65535, step=1, mode=NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
        )
