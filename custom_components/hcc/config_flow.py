from __future__ import annotations

from typing import Any, Dict

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
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

    async def _validate_and_create(self, address: str, update_minutes: int | None):
        session = async_get_clientsession(self.hass)
        client = HccApiClient(session)

        # Validate with one fetch
        try:
            await client.fetch_collection_dates(address)
        except aiohttp.ClientError:
            return None, {"base": "cannot_connect"}
        except ValueError:
            return None, {"base": "invalid_response"}
        except Exception:
            return None, {"base": "unknown"}

        await self.async_set_unique_id(f"hcc_bin_{address.lower()}")
        self._abort_if_unique_id_configured()

        data = {CONF_ADDRESS: address}
        # For imported YAML, allow interval in data; Options can still override later
        if update_minutes is not None:
            data[CONF_UPDATE_MINUTES] = update_minutes

        return self.async_create_entry(
            title=f"HCC Bin: {address}",
            data=data,
        ), None

    async def async_step_user(self, user_input: Dict[str, Any] | None = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            entry, errors = await self._validate_and_create(address, None)
            if errors is None:
                return entry

        schema = vol.Schema({vol.Required(CONF_ADDRESS): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(self, user_input: Dict[str, Any]):
        # Called when loaded from configuration.yaml
        address = user_input[CONF_ADDRESS].strip()
        minutes = int(user_input.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES))
        # Clamp minutes to allowed range
        if minutes < MIN_UPDATE_MINUTES or minutes > MAX_UPDATE_MINUTES:
            minutes = DEFAULT_UPDATE_MINUTES

        entry, errors = await self._validate_and_create(address, minutes)
        if errors is None:
            return entry
        # If import fails, abort with reason to put into logs
        return self.async_abort(reason=next(iter(errors.values()), "unknown"))

    # Optional: OptionsFlow to change interval later via UI
    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    class OptionsFlow(config_entries.OptionsFlow):
        def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
            self.config_entry = config_entry

        async def async_step_init(self, user_input: Dict[str, Any] | None = None):
            return await self.async_step_user()

        async def async_step_user(self, user_input: Dict[str, Any] | None = None):
            import voluptuous as vol
            errors: Dict[str, str] = {}
            current = self.config_entry.options.get(
                CONF_UPDATE_MINUTES,
                self.config_entry.data.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES),
            )
            if user_input is not None:
                minutes = int(user_input.get(CONF_UPDATE_MINUTES, current))
                if minutes < MIN_UPDATE_MINUTES or minutes > MAX_UPDATE_MINUTES:
                    errors["base"] = "bad_interval"
                else:
                    return self.async_create_entry(title="", data={CONF_UPDATE_MINUTES: minutes})

            schema = vol.Schema(
                {vol.Required(CONF_UPDATE_MINUTES, default=current): vol.Coerce(int)}
            )
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
