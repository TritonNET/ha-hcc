from __future__ import annotations

from typing import Optional
from datetime import date as dt_date, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ADDRESS, sanitize_address
from .coordinator import HccCoordinator, HccData

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: HccCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    entities: list[SensorEntity] = [
        HccDateSensor(coordinator, address, "HCC Red Bin Collection Date", "red", "red_bin_collection_date"),
        HccDateSensor(coordinator, address, "HCC Yellow Bin Collection Date", "yellow", "yellow_bin_collection_date"),
        HccTimestampSensor(coordinator, address, "HCC Bin Last Fetch Date", "last_fetch", "last_fetch_date"),
        HccStatusTextSensor(coordinator, address, "HCC Bin Fetch Status Text", "fetch_status_text"),
    ]
    async_add_entities(entities)

class HccBaseEntity(CoordinatorEntity[HccCoordinator]):
    _attr_should_poll = False

    def __init__(self, coordinator: HccCoordinator, address: str, name_exact: str) -> None:
        super().__init__(coordinator)
        self._address = address
        self._attr_has_entity_name = False
        self._attr_name = name_exact
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"addr:{address.lower()}")},
            "name": f"HCC Bin ({address})",
            "manufacturer": "Hamilton City Council",
            "model": "FightTheLandFill",
        }

class HccDateSensor(HccBaseEntity, SensorEntity):
    _attr_device_class = "date"

    def __init__(self, coordinator: HccCoordinator, address: str, name_exact: str, key: str, postfix: str) -> None:
        super().__init__(coordinator, address, name_exact)
        self._key = key
        sanitized = sanitize_address(address)
        base_id = f"hcc_bin_{sanitized}_{postfix}"
        self._attr_unique_id = base_id
        self.entity_id = f"sensor.{base_id}"

    @property
    def native_value(self) -> Optional[dt_date]:
        data: HccData = self.coordinator.data
        if self._key == "red":
            return data.red
        if self._key == "yellow":
            return data.yellow
        return None

class HccTimestampSensor(HccBaseEntity, SensorEntity):
    _attr_device_class = "timestamp"

    def __init__(self, coordinator: HccCoordinator, address: str, name_exact: str, key: str, postfix: str) -> None:
        super().__init__(coordinator, address, name_exact)
        self._key = key
        sanitized = sanitize_address(address)
        base_id = f"hcc_bin_{sanitized}_{postfix}"
        self._attr_unique_id = base_id
        self.entity_id = f"sensor.{base_id}"

    @property
    def native_value(self) -> Optional[datetime]:
        data: HccData = self.coordinator.data
        if self._key == "last_fetch":
            return data.last_success_fetch
        return None

class HccStatusTextSensor(HccBaseEntity, SensorEntity):
    def __init__(self, coordinator: HccCoordinator, address: str, name_exact: str, postfix: str) -> None:
        super().__init__(coordinator, address, name_exact)
        sanitized = sanitize_address(address)
        base_id = f"hcc_bin_{sanitized}_{postfix}"
        self._attr_unique_id = base_id
        self.entity_id = f"sensor.{base_id}"

    @property
    def native_value(self) -> Optional[str]:
        return self.coordinator.data.last_status_text