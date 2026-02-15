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

from .const import DOMAIN, CONF_ADDRESS, sanitize_address
from .coordinator import HccCoordinator

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HccCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    
    entities = []
    
    entities.append(HccFetchStatusBinarySensor(coordinator, address))
    
    # Config: (BinColor, Type, Pre-Key, Post-Key, Switch-Key, Due-Postfix, Name)
    tasks = [
        ("red", "out", "red_bin_put_out_pre_hours", "red_bin_put_out_post_hours", "red_bin_put_out_complete", "red_bin_put_out_due", "Red Bin Put Out Due"),
        ("red", "in", "red_bin_bring_in_pre_hours", "red_bin_bring_in_post_hours", "red_bin_bring_in_complete", "red_bin_bring_in_due", "Red Bin Bring In Due"),
        ("yellow", "out", "yellow_bin_put_out_pre_hours", "yellow_bin_put_out_post_hours", "yellow_bin_put_out_complete", "yellow_bin_put_out_due", "Yellow Bin Put Out Due"),
        ("yellow", "in", "yellow_bin_bring_in_pre_hours", "yellow_bin_bring_in_post_hours", "yellow_bin_bring_in_complete", "yellow_bin_bring_in_due", "Yellow Bin Bring In Due"),
    ]
    
    for bin_color, task_type, pre_key, post_key, switch_key, due_postfix, name in tasks:
        entities.append(
            HccBinTaskBinarySensor(
                coordinator, address, bin_color, task_type, pre_key, post_key, switch_key, due_postfix, name
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
        
        sanitized = sanitize_address(address)
        base_id = f"hcc_bin_{sanitized}_fetch_status"
        self._attr_unique_id = base_id
        self.entity_id = f"binary_sensor.{base_id}"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.last_status_ok)


class HccBinTaskBinarySensor(CoordinatorEntity[HccCoordinator], BinarySensorEntity):
    _attr_should_poll = False

    def __init__(
        self, 
        coordinator: HccCoordinator, 
        address: str, 
        bin_color: str, 
        task_type: str, 
        pre_key: str, 
        post_key: str, 
        switch_key: str,
        due_postfix: str,
        name: str
    ) -> None:
        super().__init__(coordinator)
        self._address = address
        self._bin_color = bin_color
        self._task_type = task_type
        self._pre_key = pre_key
        self._post_key = post_key
        self._switch_key = switch_key
        
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_device_class = "opening" 
        
        sanitized = sanitize_address(address)
        base_id = f"hcc_bin_{sanitized}_{due_postfix}"
        self._attr_unique_id = base_id
        self.entity_id = f"binary_sensor.{base_id}"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"addr:{address.lower()}")},
            "name": f"HCC Bin ({address})",
        }
        
        self._is_on = False
        self._unsub_timer = None
        self._unsub_trackers = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        
        self._unsub_timer = async_track_time_interval(
            self.hass, self._update_state, timedelta(minutes=1)
        )
        
        registry = er.async_get(self.hass)
        ids_to_track = []
        sanitized = sanitize_address(self._address)
        
        for key in (self._pre_key, self._post_key):
            unique_id = f"hcc_bin_{sanitized}_{key}"
            if eid := registry.async_get_entity_id("number", DOMAIN, unique_id):
                ids_to_track.append(eid)
        
        switch_uid = f"hcc_bin_{sanitized}_{self._switch_key}"
        if switch_eid := registry.async_get_entity_id("switch", DOMAIN, switch_uid):
            ids_to_track.append(switch_eid)
        
        if ids_to_track:
            self._unsub_trackers = async_track_state_change_event(
                self.hass, ids_to_track, self._update_state
            )

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
        self._update_state()
        super()._handle_coordinator_update()

    @callback
    def _update_state(self, *args):
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

        is_complete = self._is_switch_complete()
        
        if is_complete:
            if self._is_on:
                self._is_on = False
                self.async_write_ha_state()
            return

        pre_hours = self._get_number_value(self._pre_key, 6.0)
        post_hours = self._get_number_value(self._post_key, 8.0)

        local_midnight = dt_util.start_of_local_day(
            dt_util.as_local(datetime.combine(collection_date, time.min))
        )
        
        if self._task_type == "out":
            start_dt = local_midnight - timedelta(hours=pre_hours)
            end_dt = local_midnight + timedelta(hours=post_hours)
        else:
            anchor = local_midnight + timedelta(days=1)
            start_dt = anchor - timedelta(hours=pre_hours)
            end_dt = anchor + timedelta(hours=post_hours)

        now = dt_util.now()
        is_active = start_dt <= now <= end_dt

        if self._is_on != is_active:
            self._is_on = is_active
            self.async_write_ha_state()

    def _get_number_value(self, key_suffix: str, default: float) -> float:
        sanitized = sanitize_address(self._address)
        unique_id = f"hcc_bin_{sanitized}_{key_suffix}"
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
        sanitized = sanitize_address(self._address)
        unique_id = f"hcc_bin_{sanitized}_{self._switch_key}"
        ent_reg = er.async_get(self.hass)
        entity_id = ent_reg.async_get_entity_id("switch", DOMAIN, unique_id)
        
        if entity_id:
            state = self.hass.states.get(entity_id)
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