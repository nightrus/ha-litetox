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
    attrs: Callable[[dict[str, Any]], dict[str, Any]] | None = None


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
    LitetoxBinaryDescription(
        key="webasto_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        # unknown until the first cmd_READ reply; the server asks hourly
        value=lambda d: bool(d.get("webasto_error")) if d.get("webasto_diag_ts") else None,
        attrs=lambda d: {"error_code": d.get("webasto_error"), "report": d.get("webasto_diag_raw"),
                         "updated": d.get("webasto_diag_ts")},
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        desc = self.entity_description
        return desc.attrs(self.d) if desc.attrs else None
