"""Polling coordinator for one tracker on a litetox server."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LitetoxAuthError, LitetoxClient, LitetoxError, LitetoxNotFound, LitetoxOffline
from .const import (
    COMMAND_POLL,
    COMMAND_TIMEOUT,
    CONF_IMEI,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

type LitetoxConfigEntry = ConfigEntry[LitetoxCoordinator]


class LitetoxCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holds the server-side state of the tracker."""

    config_entry: LitetoxConfigEntry

    def __init__(self, hass: HomeAssistant, entry: LitetoxConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.data[CONF_IMEI]}",
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.imei: str = entry.data[CONF_IMEI]
        self.client = LitetoxClient(
            async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_API_TOKEN]
        )
        # optimistic heater state after START/STOP until the module confirms
        self.heater_pending: tuple[bool, float] | None = None
        self._watchers: set[asyncio.Task] = set()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.state(self.imei)
        except LitetoxAuthError as err:
            raise ConfigEntryAuthFailed("invalid token") from err
        except LitetoxNotFound as err:
            raise UpdateFailed(f"IMEI {self.imei} is not registered on the server") from err
        except LitetoxError as err:
            raise UpdateFailed(str(err)) from err
        if self.heater_pending:
            want, since = self.heater_pending
            if data.get("heater_on") == want or time.monotonic() - since > COMMAND_TIMEOUT:
                self.heater_pending = None
        return data

    async def async_send(self, command: str) -> None:
        """Send a raw module command (the server adds the cmd_ prefix)."""
        try:
            cmd_id = await self.client.command(self.imei, command)
        except LitetoxOffline as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="device_offline"
            ) from err
        except LitetoxError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        if cmd_id:
            task = self.config_entry.async_create_background_task(
                self.hass, self._watch(cmd_id), f"{DOMAIN} command {cmd_id}"
            )
            self._watchers.add(task)
            task.add_done_callback(self._watchers.discard)

    async def _watch(self, cmd_id: int) -> None:
        """Refresh as soon as the module answers instead of waiting for the next poll."""
        deadline = time.monotonic() + COMMAND_TIMEOUT
        while time.monotonic() < deadline:
            await asyncio.sleep(COMMAND_POLL)
            try:
                st = await self.client.command_status(self.imei, cmd_id)
            except LitetoxError:
                continue
            if st.get("status") in ("answered", "failed", "expired"):
                break
        await self.async_refresh()
