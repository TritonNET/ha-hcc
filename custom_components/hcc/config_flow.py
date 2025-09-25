from __future__ import annotations

from typing import Any, Dict
from datetime import timedelta

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_ADDRESS,
    CONF_UPDATE_MINUTES,
    DEFAULT_UPDATE_MINUTES,
    MIN_UPDATE_MINUTES,
    MAX_UPDATE_MINUTES,
)
from .api import HccApiClient

class HccConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None):
        errors: Dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            # Validate by attempting one fetch
            session = async_get_clientsession(self.hass)
            client = HccApiClient(session)

            try:
                await client.fetch_collection_dates(address)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_response"
            except Exception:
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(f"hcc_bin_{address.lower()}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"HCC Bin: {address}",
                    data={CONF_ADDRESS: address},
                    options={CONF_UPDATE_MINUTES: DEFAULT_UPDATE_MINUTES},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_options(self):
        return await self.async_step_options_user()

    async def async_step_options_user(self, user_input: Dict[str, Any] | None = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            minutes = int(user_input.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES))
            if minutes < MIN_UPDATE_MINUTES or minutes > MAX_UPDATE_MINUTES:
                errors["base"] = "bad_interval"
            else:
                return self.async_create_entry(title="", data={CONF_UPDATE_MINUTES: minutes})

        current = self.config_entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES)
        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_MINUTES, default=current): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="options_user", data_schema=schema, errors=errors)

    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    class OptionsFlow(config_entries.OptionsFlow):
        def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
            self.config_entry = config_entry

        async def async_step_init(self, user_input: Dict[str, Any] | None = None):
            return await self.async_step_user()

        async def async_step_user(self, user_input: Dict[str, Any] | None = None):
            errors: Dict[str, str] = {}
            if user_input is not None:
                minutes = int(user_input.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES))
                if minutes < MIN_UPDATE_MINUTES or minutes > MAX_UPDATE_MINUTES:
                    errors["base"] = "bad_interval"
                else:
                    return self.async_create_entry(title="", data={CONF_UPDATE_MINUTES: minutes})

            current = self.config_entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES)
            schema = vol.Schema(
                {
                    vol.Required(CONF_UPDATE_MINUTES, default=current): vol.Coerce(int),
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
