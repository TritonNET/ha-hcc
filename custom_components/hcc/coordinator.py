from __future__ import annotations

from datetime import timedelta, datetime, timezone
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import aiohttp

from .api import HccApiClient
from .const import (
    DOMAIN,
    STATUS_SUCCESS,
    STATUS_NETWORK,
    STATUS_JSON,
    STATUS_UNEXPECTED,
)

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
            hass.helpers.logger.logging.getLogger(f"{DOMAIN}.coordinator"),
            name="HCC Bin Coordinator",
            update_interval=update_interval,
        )
        self._address = address
        self._client = HccApiClient(session)
        self.data = HccData()  # keep last successful data

    async def _async_update_data(self) -> HccData:
        """
        We NEVER raise UpdateFailed here because we want entities to retain last successful values.
        On failure, we just update status fields and return self.data unchanged.
        """
        try:
            red_dt, yellow_dt = await self._client.fetch_collection_dates(self._address)
            # Successful fetch
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
