from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_ADDRESS, sanitize_address

# Define the configuration structure for our 8 numbers
NUMBER_TYPES = [
    ("red_bin_put_out_pre_hours", "Red Bin Put Out Pre Hours", 6.0),
    ("red_bin_put_out_post_hours", "Red Bin Put Out Post Hours", 8.0),
    ("red_bin_bring_in_pre_hours", "Red Bin Bring In Pre Hours", 4.0),
    ("red_bin_bring_in_post_hours", "Red Bin Bring In Post Hours", 5.0),
    ("yellow_bin_put_out_pre_hours", "Yellow Bin Put Out Pre Hours", 6.0),
    ("yellow_bin_put_out_post_hours", "Yellow Bin Put Out Post Hours", 8.0),
    ("yellow_bin_bring_in_pre_hours", "Yellow Bin Bring In Pre Hours", 4.0),
    ("yellow_bin_bring_in_post_hours", "Yellow Bin Bring In Post Hours", 5.0),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    address = entry.data[CONF_ADDRESS]
    entities = []
    
    for key, name, default_val in NUMBER_TYPES:
        entities.append(HccWindowNumber(address, key, name, default_val))
        
    async_add_entities(entities)

class HccWindowNumber(RestoreEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 48
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "h"

    def __init__(self, address: str, key: str, name: str, default_val: float) -> None:
        self._address = address
        self._key = key
        self._attr_name = name
        self._default_val = default_val
        
        sanitized = sanitize_address(address)
        base_id = f"hcc_bin_{sanitized}_{key}"
        self._attr_unique_id = base_id
        self.entity_id = f"number.{base_id}"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"addr:{address.lower()}")},
            "name": f"HCC Bin ({address})",
            "manufacturer": "Hamilton City Council",
            "model": "FightTheLandFill",
        }
        
        self._attr_native_value = default_val

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in ("unknown", "unavailable"):
                try:
                    self._attr_native_value = float(last_state.state)
                except ValueError:
                    pass

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()