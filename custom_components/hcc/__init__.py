from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS, CONF_ADDRESS, CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES
from .coordinator import HccCoordinator

type HccConfigEntry = ConfigEntry

async def async_setup_entry(hass: HomeAssistant, entry: HccConfigEntry) -> bool:
    address = entry.data[CONF_ADDRESS]
    minutes = entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES)

    session = async_get_clientsession(hass)
    coordinator = HccCoordinator(
        hass=hass,
        address=address,
        update_interval=timedelta(minutes=minutes),
        session=session,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: HccConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
