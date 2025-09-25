from __future__ import annotations

from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_ADDRESS,
    CONF_UPDATE_MINUTES,
    DEFAULT_UPDATE_MINUTES,
    MIN_UPDATE_MINUTES,
    MAX_UPDATE_MINUTES,
)
from .coordinator import HccCoordinator

# ----- YAML configuration schema -----
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_ADDRESS): cv.string,
                        vol.Optional(
                            CONF_UPDATE_MINUTES, default=DEFAULT_UPDATE_MINUTES
                        ): vol.All(int, vol.Range(min=MIN_UPDATE_MINUTES, max=MAX_UPDATE_MINUTES)),
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Support YAML by importing entries into Config Entries
async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    yaml_list = config.get(DOMAIN)
    if not yaml_list:
        return True

    for item in yaml_list:
        data = {
            CONF_ADDRESS: item[CONF_ADDRESS].strip(),
            # Put interval into data for import; Options Flow can still change it later
            CONF_UPDATE_MINUTES: item.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES),
        }
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=data,
            )
        )
    return True

type HccConfigEntry = config_entries.ConfigEntry

async def async_setup_entry(hass: HomeAssistant, entry: HccConfigEntry) -> bool:
    address = entry.data[CONF_ADDRESS]
    # Read minutes from options if present, else fall back to data (YAML import), then default
    minutes = entry.options.get(
        CONF_UPDATE_MINUTES,
        entry.data.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES),
    )

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
