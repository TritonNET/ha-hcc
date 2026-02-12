from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta, time

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.event import async_track_time_interval, async_track_state_change_event
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_ADDRESS
from .coordinator import HccCoordinator

ENTITY_ID_STATUS = "binary_sensor.hcc_bin_collection_info_fetch_status"

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HccCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    
    entities = []
    
    # 1. Existing Status Sensor
    entities.append(HccFetchStatusBinarySensor(coordinator, address))
    
    # 2. New Task Sensors (Red Out/In, Yellow Out/In)
    # Config: (BinColor, Type, Pre-Key, Post-Key, Name)
    tasks = [
        ("red", "out", "red_out_pre", "red_out_post", "Red Bin Put Out Due"),
        ("red", "in", "red_in_pre", "red_in_post", "Red Bin Bring In Due"),
        ("yellow", "out", "yellow_out_pre", "yellow_out_post", "Yellow Bin Put Out Due"),
        ("yellow", "in", "yellow_in_pre", "yellow_in_post", "Yellow Bin Bring In Due"),
    ]
    
    for bin_color, task_type, pre_key, post_key, name in tasks:
        entities.append(
            HccBinTaskBinarySensor(
                coordinator, address, bin_color, task_type, pre_key, post_key, name
            )
        )

    async_add_entities(entities)


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
        self.entity_id = ENTITY_ID_STATUS

    @property
    def is_on(self) -> bool:
        # True means last fetch succeeded
        return bool(self.coordinator.data.last_status_ok)


class HccBinTaskBinarySensor(CoordinatorEntity[HccCoordinator], BinarySensorEntity):
    """
    Binary sensor that is ON when a bin task is DUE.
    Is OFF if the window is closed OR if the completion switch is ON.
    """
    _attr_should_poll = False

    def __init__(
        self, 
        coordinator: HccCoordinator, 
        address: str, 
        bin_color: str, 
        task_type: str, 
        pre_key: str, 
        post_key: str, 
        name: str
    ) -> None:
        super().__init__(coordinator)
        self._address = address
        self._bin_color = bin_color      # "red" or "yellow"
        self._task_type = task_type      # "out" or "in"
        self._pre_key = pre_key
        self._post_key = post_key
        
        self._attr_has_entity_name = True
        self._attr_name = name
        # "opening" is a reasonable class for a time window
        self._attr_device_class = "opening" 
        
        # Unique ID 
        self._attr_unique_id = f"{DOMAIN}_{address.lower()}_{bin_color}_{task_type}_due"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"addr:{address.lower()}")},
            "name": f"HCC Bin ({address})",
        }
        
        self._is_on = False
        
        # Cleanup handles
        self._unsub_timer = None
        self._unsub_trackers = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        
        # 1. Update every minute to check if time window opens/closes
        self._unsub_timer = async_track_time_interval(
            self.hass, self._update_state, timedelta(minutes=1)
        )
        
        # 2. Listen for changes to associated entities (Numbers AND Switch)
        registry = er.async_get(self.hass)
        ids_to_track = []
        
        # A) Track Number Entities (pre/post)
        for key in (self._pre_key, self._post_key):
            unique_id = f"{DOMAIN}_{self._address.lower()}_{key}"
            if eid := registry.async_get_entity_id("number", DOMAIN, unique_id):
                ids_to_track.append(eid)
        
        # B) Track Completion Switch Entity
        # Unique ID pattern must match switch.py: {DOMAIN}_{address}_{color}_{type}_complete
        switch_uid = f"{DOMAIN}_{self._address.lower()}_{self._bin_color}_{self._task_type}_complete"
        if switch_eid := registry.async_get_entity_id("switch", DOMAIN, switch_uid):
            ids_to_track.append(switch_eid)
        
        # If we found any entities, track their state changes
        if ids_to_track:
            self._unsub_trackers = async_track_state_change_event(
                self.hass, ids_to_track, self._update_state
            )

        # Initial calculation
        self._update_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        if self._unsub_trackers:
            self._unsub_trackers()
            self._unsub_trackers = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator immediately."""
        self._update_state()
        super()._handle_coordinator_update()

    @callback
    def _update_state(self, *args):
        """Calculate if the task is currently due."""
        # 1. Get Coordinator Data
        data = self.coordinator.data
        if not data:
            self._is_on = False
            self.async_write_ha_state()
            return

        collection_date = data.red if self._bin_color == "red" else data.yellow
        if not collection_date:
            self._is_on = False
            self.async_write_ha_state()
            return

        # 2. Check if "Completion Switch" is ON (Dynamic Lookup)
        # If complete, "Due" is False regardless of time window
        is_complete = self._is_switch_complete()
        
        if is_complete:
            # If switch is ON, the task is done -> Due is OFF
            if self._is_on:
                self._is_on = False
                self.async_write_ha_state()
            return

        # 3. Calculate Time Window
        pre_hours = self._get_number_value(self._pre_key, 6.0)
        post_hours = self._get_number_value(self._post_key, 8.0)

        # Convert date to aware datetime at midnight local time
        local_midnight = dt_util.start_of_local_day(
            dt_util.as_local(datetime.combine(collection_date, time.min))
        )
        
        if self._task_type == "out":
            # Put Out Window
            start_dt = local_midnight - timedelta(hours=pre_hours)
            end_dt = local_midnight + timedelta(hours=post_hours)
        else:
            # Bring In Window
            anchor = local_midnight + timedelta(days=1)
            start_dt = anchor - timedelta(hours=pre_hours)
            end_dt = anchor + timedelta(hours=post_hours)

        # 4. Compare with Now
        now = dt_util.now()
        is_active = start_dt <= now <= end_dt

        if self._is_on != is_active:
            self._is_on = is_active
            self.async_write_ha_state()

    def _get_number_value(self, key_suffix: str, default: float) -> float:
        """Helper to find the state of the associated number entity."""
        unique_id = f"{DOMAIN}_{self._address.lower()}_{key_suffix}"
        ent_reg = er.async_get(self.hass)
        entity_id = ent_reg.async_get_entity_id("number", DOMAIN, unique_id)
        
        if entity_id:
            state = self.hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except ValueError:
                    pass
        return default

    def _is_switch_complete(self) -> bool:
        """Check if the corresponding completion switch is ON."""
        unique_id = f"{DOMAIN}_{self._address.lower()}_{self._bin_color}_{self._task_type}_complete"
        ent_reg = er.async_get(self.hass)
        entity_id = ent_reg.async_get_entity_id("switch", DOMAIN, unique_id)
        
        if entity_id:
            state = self.hass.states.get(entity_id)
            # We check explicitly for "on"
            if state and state.state == "on":
                return True
        return False

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def extra_state_attributes(self):
        return {
            "bin": self._bin_color,
            "task": self._task_type
        }