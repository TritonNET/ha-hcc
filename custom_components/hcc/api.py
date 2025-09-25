from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timezone

import aiohttp
from .const import API_BASE

class HccApiClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def fetch_collection_dates(self, address: str, timeout_sec: int = 10) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Calls the API and returns (red_dt, yellow_dt) in UTC or None if missing.
        Raises:
            aiohttp.ClientError for network issues
            ValueError for JSON parsing / shape issues
        """
        params = {"address_string": address}
        # Explicit timeout
        try:
            async with self._session.get(API_BASE, params=params, timeout=timeout_sec) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except asyncio.TimeoutError as ex:
            raise ex
        except aiohttp.ClientError as ex:
            raise ex

        if not isinstance(data, list) or not data:
            raise ValueError("Unexpected JSON shape: not a non-empty list")

        item = data[0]
        if not isinstance(item, dict):
            raise ValueError("Unexpected JSON shape: first element is not an object")

        red_raw = item.get("RedBin")
        yellow_raw = item.get("YellowBin")

        def parse_ts(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            # Format: "2025-10-08T00:00:00"
            try:
                dt = datetime.fromisoformat(s)
                # Assume naive timestamps are local NZ date; to keep it simple treat as naive UTC midnight
                # but better: treat as naive and set tz to UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception as ex:
                raise ValueError(f"Invalid timestamp: {s}") from ex

        red_dt = parse_ts(red_raw)
        yellow_dt = parse_ts(yellow_raw)

        return red_dt, yellow_dt
