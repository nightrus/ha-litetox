"""Request buttons: status, balance, GSM cells."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LitetoxConfigEntry
from .entity import LitetoxEntity


@dataclass(frozen=True, kw_only=True)
class LitetoxButtonDescription(ButtonEntityDescription):
    command: str


BUTTONS: tuple[LitetoxButtonDescription, ...] = (
    LitetoxButtonDescription(key="request_status", command="STATUS", icon="mdi:refresh"),
    LitetoxButtonDescription(key="request_balance", command="ussd", icon="mdi:cash-sync"),
    LitetoxButtonDescription(
        key="request_cells", command="gsminfo", icon="mdi:radio-tower",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LitetoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(LitetoxButton(entry.runtime_data, desc) for desc in BUTTONS)


class LitetoxButton(LitetoxEntity, ButtonEntity):
    entity_description: LitetoxButtonDescription

    def __init__(self, coordinator, description: LitetoxButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.coordinator.async_send(self.entity_description.command)
