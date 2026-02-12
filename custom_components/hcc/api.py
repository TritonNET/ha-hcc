from __future__ import annotations

from typing import Optional, Tuple
from datetime import datetime, date as dt_date
import asyncio
import aiohttp

from .const import API_BASE

class HccApiClient:
    def __init__(self, session: aiohttp.ClientSession, api_url: str = API_BASE) -> None:
        self._session = session
        self._api_url = api_url

    async def fetch_collection_dates(self, address: str, timeout_sec: int = 10) -> Tuple[Optional[dt_date], Optional[dt_date]]:
        """
        Calls the API and returns (red_date, yellow_date) as date objects (no time).
        """
        params = {"address_string": address}
        try:
            async with self._session.get(self._api_url, params=params, timeout=timeout_sec) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except asyncio.TimeoutError as ex:
            raise ex
        except aiohttp.ClientError as ex:
            raise ex

        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            raise ValueError("Unexpected JSON shape")

        item = data[0]
        red_raw = item.get("RedBin")
        yellow_raw = item.get("YellowBin")

        def parse_date(s: Optional[str]) -> Optional[dt_date]:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s).date()
            except Exception as ex:
                raise ValueError(f"Invalid timestamp: {s}") from ex

        red_date = parse_date(red_raw)
        yellow_date = parse_date(yellow_raw)
        return red_date, yellow_date