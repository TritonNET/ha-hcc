from __future__ import annotations

from datetime import timedelta, datetime, timezone, date as dt_date
from typing import Optional
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import HccApiClient
from .const import DOMAIN, STATUS_SUCCESS, STATUS_NETWORK, STATUS_JSON, STATUS_UNEXPECTED, API_BASE

_LOGGER = logging.getLogger(__name__)

class HccData:
    def __init__(self) -> None:
        self.red: Optional[dt_date] = None
        self.yellow: Optional[dt_date] = None
        self.last_success_fetch: Optional[datetime] = None
        self.last_status_ok: bool = False
        self.last_status_text: str = STATUS_UNEXPECTED

class HccCoordinator(DataUpdateCoordinator[HccData]):
    # Add api_url argument
    def __init__(self, hass: HomeAssistant, address: str, update_interval: timedelta, session: aiohttp.ClientSession, api_url: str) -> None:
        super().__init__(hass, _LOGGER, name="HCC Bin Coordinator", update_interval=update_interval)
        self._address = address
        # Pass api_url to the client
        self._client = HccApiClient(session, api_url=api_url)
        self.data = HccData()

    async def _async_update_data(self) -> HccData:
        try:
            red_date, yellow_date = await self._client.fetch_collection_dates(self._address)
            self.data.red = red_date
            self.data.yellow = yellow_date
            self.data.last_success_fetch = datetime.now(timezone.utc)
            self.data.last_status_ok = True
            self.data.last_status_text = STATUS_SUCCESS
        except aiohttp.ClientError:
            self.data.last_status_ok = False
            self.data.last_status_text = STATUS_NETWORK
        except ValueError:
            self.data.last_status_ok = False
            self.data.last_status_text = STATUS_JSON
        except Exception:
            self.data.last_status_ok = False
            self.data.last_status_text = STATUS_UNEXPECTED

        return self.data