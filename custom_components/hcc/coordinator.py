from __future__ import annotations

from datetime import timedelta, datetime, timezone
from typing import Optional
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import HccApiClient
from .const import (
    DOMAIN,
    STATUS_SUCCESS,
    STATUS_NETWORK,
    STATUS_JSON,
    STATUS_UNEXPECTED,
)

_LOGGER = logging.getLogger(__name__)


class HccData:
    def __init__(self) -> None:
        self.red: Optional[datetime] = None
        self.yellow: Optional[datetime] = None
        self.last_success_fetch: Optional[datetime] = None  # UTC
        self.last_status_ok: bool = False
        self.last_status_text: str = STATUS_UNEXPECTED


class HccCoordinator(DataUpdateCoordinator[HccData]):
    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        update_interval: timedelta,
        session: aiohttp.ClientSession,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,  # <-- standard logger
            name="HCC Bin Coordinator",
            update_interval=update_interval,
        )
        self._address = address
        self._client = HccApiClient(session)
        self.data = HccData()  # keep last successful data

    async def _async_update_data(self) -> HccData:
        """
        On failure we keep previous values and set status fields;
        we do not raise UpdateFailed so sensors keep last good value.
        """
        try:
            red_dt, yellow_dt = await self._client.fetch_collection_dates(self._address)
            self.data.red = red_dt
            self.data.yellow = yellow_dt
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
