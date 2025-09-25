from __future__ import annotations

from typing import Any, Optional
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ADDRESS
from .coordinator import HccCoordinator, HccData

SENSOR_IDS = {
    "red": "sensor.hcc_bin_collection_date_red",
    "yellow": "sensor.hcc_bin_collection_date_yellow",
    "last_fetch": "sensor.hcc_bin_collection_info_last_fetch_date",
    "status_text": "sensor.hcc_bin_collection_info_fetch_status_text",
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: HccCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    entities: list[SensorEntity] = [
        HccTimestampSensor(coordinator, address, "Red Bin Collection Date", "red", SENSOR_IDS["red"]),
        HccTimestampSensor(coordinator, address, "Yellow Bin Collection Date", "yellow", SENSOR_IDS["yellow"]),
        HccTimestampSensor(coordinator, address, "Last Fetch Date", "last_fetch", SENSOR_IDS["last_fetch"]),
        HccStatusTextSensor(coordinator, address, "Fetch Status Text", SENSOR_IDS["status_text"]),
    ]
    async_add_entities(entities)

class HccBaseEntity(CoordinatorEntity[HccCoordinator]):
    _attr_should_poll = False

    def __init__(self, coordinator: HccCoordinator, address: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._address = address
        self._attr_has_entity_name = True
        self._attr_name = f"HCC Bin {name_suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"addr:{address.lower()}")},
            "name": f"HCC Bin ({address})",
            "manufacturer": "Hamilton City Council",
            "model": "FightTheLandFill",
        }

class HccTimestampSensor(HccBaseEntity, SensorEntity):
    _attr_device_class = "timestamp"

    def __init__(self, coordinator: HccCoordinator, address: str, name_suffix: str, key: str, entity_id_forced: str) -> None:
        super().__init__(coordinator, address, name_suffix)
        self._key = key
        self.entity_id = entity_id_forced
        self._attr_unique_id = f"{DOMAIN}_{address.lower()}_{key}"

    @property
    def native_value(self) -> Optional[datetime]:
        data: HccData = self.coordinator.data
        if self._key == "red":
            return data.red
        if self._key == "yellow":
            return data.yellow
        if self._key == "last_fetch":
            return data.last_success_fetch
        return None

class HccStatusTextSensor(HccBaseEntity, SensorEntity):
    def __init__(self, coordinator: HccCoordinator, address: str, name_suffix: str, entity_id_forced: str) -> None:
        super().__init__(coordinator, address, name_suffix)
        self.entity_id = entity_id_forced
        self._attr_unique_id = f"{DOMAIN}_{address.lower()}_status_text"

    @property
    def native_value(self) -> Optional[str]:
        return self.coordinator.data.last_status_text
