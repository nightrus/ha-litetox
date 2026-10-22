"""GPS position of the tracker."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LitetoxConfigEntry
from .entity import LitetoxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LitetoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([LitetoxTracker(entry.runtime_data)])


class LitetoxTracker(LitetoxEntity, TrackerEntity):
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "location")

    @property
    def latitude(self) -> float | None:
        return self.d.get("latitude")

    @property
    def longitude(self) -> float | None:
        return self.d.get("longitude")

    @property
    def location_accuracy(self) -> float:
        # HDOP × ~5 m user-equivalent range error; 0 means "unknown" for HA
        hdop = self.d.get("hdop")
        return round(hdop * 5, 1) if hdop else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.d
        return {
            "speed": d.get("speed"),
            "course": d.get("course"),
            "satellites": d.get("satellites"),
            "position_time": d.get("position_ts"),
        }
