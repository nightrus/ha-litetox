"""Sensors for Litetox Proxy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import LitetoxConfigEntry
from .entity import LitetoxEntity


def _ts(key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda d: dt_util.parse_datetime(d[key]) if d.get(key) else None


@dataclass(frozen=True, kw_only=True)
class LitetoxSensorDescription(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any] | None = None
    attrs: Callable[[dict[str, Any]], dict[str, Any]] | None = None


DIAG = EntityCategory.DIAGNOSTIC

SENSORS: tuple[LitetoxSensorDescription, ...] = (
    LitetoxSensorDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    LitetoxSensorDescription(
        key="cabin_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    LitetoxSensorDescription(
        key="heater_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    LitetoxSensorDescription(
        key="heater_minutes",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value=lambda d: d.get("heater_minutes") if d.get("heater_on") else 0,
    ),
    LitetoxSensorDescription(
        key="balance",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        attrs=lambda d: {"updated": d.get("balance_ts"), "ussd_reply": d.get("ussd_raw")},
    ),
    LitetoxSensorDescription(
        key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    LitetoxSensorDescription(
        key="odometer_km",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    LitetoxSensorDescription(
        key="gsm",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=DIAG,
        icon="mdi:signal",
    ),
    LitetoxSensorDescription(
        key="satellites",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=DIAG,
    ),
    LitetoxSensorDescription(key="hdop", entity_category=DIAG, entity_registry_enabled_default=False),
    LitetoxSensorDescription(
        key="altitude",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        entity_category=DIAG,
        entity_registry_enabled_default=False,
    ),
    LitetoxSensorDescription(
        key="gsm_cell",
        entity_category=DIAG,
        attrs=lambda d: {"cells": d.get("gsm_cells"), "updated": d.get("cells_ts")},
    ),
    LitetoxSensorDescription(key="firmware", entity_category=DIAG),
    LitetoxSensorDescription(
        key="last_seen", device_class=SensorDeviceClass.TIMESTAMP, entity_category=DIAG,
        value=_ts("last_seen"),
    ),
    LitetoxSensorDescription(
        key="position_ts", device_class=SensorDeviceClass.TIMESTAMP, entity_category=DIAG,
        value=_ts("position_ts"),
    ),
    LitetoxSensorDescription(
        key="heater_ts", device_class=SensorDeviceClass.TIMESTAMP, entity_category=DIAG,
        value=_ts("heater_ts"),
        attrs=lambda d: {"status": d.get("heater_raw")},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LitetoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(LitetoxSensor(entry.runtime_data, desc) for desc in SENSORS)


class LitetoxSensor(LitetoxEntity, SensorEntity):
    entity_description: LitetoxSensorDescription

    def __init__(self, coordinator, description: LitetoxSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        desc = self.entity_description
        return desc.value(self.d) if desc.value else self.d.get(desc.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        desc = self.entity_description
        return desc.attrs(self.d) if desc.attrs else None
