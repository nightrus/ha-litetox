"""Litetox Server — ALTOX heater/tracker via own Wialon IPS server."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.const import CONF_API_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import LitetoxClient, LitetoxError
from .const import (
    ATTR_COMMAND,
    ATTR_DEVICE_ID,
    ATTR_MINUTES,
    CONF_IMEI,
    DOMAIN,
    SERVICE_SEND_COMMAND,
    SERVICE_START_HEATER,
)
from .coordinator import LitetoxConfigEntry, LitetoxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.SWITCH,
]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_SEND_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_COMMAND): vol.All(cv.string, vol.Length(min=1, max=200)),
    }
)
_START_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=10, max=120)),
    }
)


def _coordinator(hass: HomeAssistant, call: ServiceCall) -> LitetoxCoordinator:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    device_id = call.data.get(ATTR_DEVICE_ID)
    if device_id:
        device = dr.async_get(hass).async_get(device_id)
        entries = [e for e in entries if device and e.entry_id in device.config_entries]
    if len(entries) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_required" if not device_id else "device_unknown",
        )
    return entries[0].runtime_data


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def send_command(call: ServiceCall) -> None:
        await _coordinator(hass, call).async_send(call.data[ATTR_COMMAND])

    async def start_heater(call: ServiceCall) -> None:
        coord = _coordinator(hass, call)
        minutes = call.data.get(ATTR_MINUTES)
        await coord.async_send(f"START:{minutes}" if minutes else "START")

    hass.services.async_register(DOMAIN, SERVICE_SEND_COMMAND, send_command, _SEND_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_START_HEATER, start_heater, _START_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LitetoxConfigEntry) -> bool:
    coordinator = LitetoxCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LitetoxConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: LitetoxConfigEntry) -> None:
    """Integration removed → the server stops accepting this tracker."""
    client = LitetoxClient(
        async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_API_TOKEN]
    )
    try:
        await client.unregister(entry.data[CONF_IMEI])
    except LitetoxError as err:
        _LOGGER.warning("Could not unregister %s on the server: %s", entry.data[CONF_IMEI], err)
