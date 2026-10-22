"""Base entity for Litetox Proxy."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LitetoxCoordinator


class LitetoxEntity(CoordinatorEntity[LitetoxCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: LitetoxCoordinator, key: str) -> None:
        super().__init__(coordinator)
        imei = coordinator.imei
        self._attr_unique_id = f"{imei}_{key}"
        self._attr_translation_key = key
        data = coordinator.data or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, imei)},
            name=coordinator.config_entry.data.get(CONF_NAME) or imei,
            manufacturer="ALTOX",
            model="Wialon IPS tracker",
            serial_number=imei,
            sw_version=data.get("firmware"),
        )

    @property
    def d(self) -> dict[str, Any]:
        return self.coordinator.data or {}
