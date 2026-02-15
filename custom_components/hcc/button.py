from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ADDRESS, sanitize_address
from .coordinator import HccCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HccCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    
    async_add_entities([HccRefreshButton(coordinator, address)])

class HccRefreshButton(CoordinatorEntity[HccCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Refresh Collection Data"

    def __init__(self, coordinator: HccCoordinator, address: str) -> None:
        super().__init__(coordinator)
        self._address = address
        
        sanitized = sanitize_address(address)
        base_id = f"hcc_bin_{sanitized}_refresh_collection_data"
        self._attr_unique_id = base_id
        self.entity_id = f"button.{base_id}"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"addr:{address.lower()}")},
            "name": f"HCC Bin ({address})",
            "manufacturer": "Hamilton City Council",
            "model": "FightTheLandFill",
        }

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()