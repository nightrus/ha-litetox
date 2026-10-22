"""Binary sensors for Litetox Server."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LitetoxConfigEntry
from .entity import LitetoxEntity


@dataclass(frozen=True, kw_only=True)
class LitetoxBinaryDescription(BinarySensorEntityDescription):
    value: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[LitetoxBinaryDescription, ...] = (
    LitetoxBinaryDescription(
        key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("online"),
    ),
    LitetoxBinaryDescription(
        key="heater",
        device_class=BinarySensorDeviceClass.RUNNING,
        value=lambda d: d.get("heater_on"),
    ),
    LitetoxBinaryDescription(
        key="flame",
        device_class=BinarySensorDeviceClass.HEAT,
        value=lambda d: d.get("flame"),
    ),
    LitetoxBinaryDescription(
        key="moving",
        device_class=BinarySensorDeviceClass.MOVING,
        value=lambda d: d.get("moving"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LitetoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(LitetoxBinarySensor(entry.runtime_data, desc) for desc in BINARY_SENSORS)


class LitetoxBinarySensor(LitetoxEntity, BinarySensorEntity):
    entity_description: LitetoxBinaryDescription

    def __init__(self, coordinator, description: LitetoxBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value(self.d)
