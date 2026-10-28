"""Heater and OUT output switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_HEATER_MINUTES, DEFAULT_HEATER_MINUTES
from .coordinator import LitetoxConfigEntry
from .entity import LitetoxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LitetoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coord = entry.runtime_data
    async_add_entities([HeaterSwitch(coord), OutputSwitch(coord)])


class HeaterSwitch(LitetoxEntity, SwitchEntity):
    """START/STOP. Shows the requested state until the module confirms (≤90 s)."""

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "heater_switch")

    @property
    def is_on(self) -> bool | None:
        pending = self.coordinator.heater_pending
        if pending:
            return pending[0]
        return self.d.get("heater_on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        minutes = self.coordinator.config_entry.options.get(
            CONF_HEATER_MINUTES, DEFAULT_HEATER_MINUTES
        )
        await self.coordinator.async_heater(True, minutes)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_heater(False)


class OutputSwitch(LitetoxEntity, SwitchEntity):
    """Extra output OUT (ACTIVATE/DEACTIVATE). Off by default — most installs
    drive it automatically (pump/fan) unless SEPAROUT1 is set."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "output")

    @property
    def is_on(self) -> bool | None:
        return self.d.get("heater_output")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send("ACTIVATE")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send("DEACTIVATE")
