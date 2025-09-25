from __future__ import annotations

from typing import Optional

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ADDRESS
from .coordinator import HccCoordinator

ENTITY_ID = "binary_sensor.hcc_bin_collection_info_fetch_status"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: HccCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    async_add_entities([HccFetchStatusBinarySensor(coordinator, address)])

class HccFetchStatusBinarySensor(CoordinatorEntity[HccCoordinator], BinarySensorEntity):
    _attr_should_poll = False

    def __init__(self, coordinator: HccCoordinator, address: str) -> None:
        super().__init__(coordinator)
        self._address = address
        self._attr_has_entity_name = True
        self._attr_name = "HCC Bin Fetch Status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"addr:{address.lower()}")},
            "name": f"HCC Bin ({address})",
            "manufacturer": "Hamilton City Council",
            "model": "FightTheLandFill",
        }
        self._attr_unique_id = f"{DOMAIN}_{address.lower()}_fetch_status"
        self.entity_id = ENTITY_ID

    @property
    def is_on(self) -> bool:
        # True means last fetch succeeded
        return bool(self.coordinator.data.last_status_ok)
