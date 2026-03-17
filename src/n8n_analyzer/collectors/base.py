"""BaseCollector — shared httpx client with timeout and single-retry logic."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PartialDataError(Exception):
    """Raised when a secondary data source is unavailable after retry.

    Callers should catch this and render a DATA UNAVAILABLE section rather
    than aborting the analysis run (FR-014).
    """

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"[{source}] {reason}")


class BaseCollector:
    """Abstract base for HTTP-based data collectors.

    Provides:
    - Shared httpx.AsyncClient with configured timeout
    - One automatic retry on 5xx / connection errors (FR-009)
    - Raises PartialDataError on secondary-source failure; callers handle primary failure
    """

    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout=float(timeout_seconds))
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """HTTP GET with one retry on transient failure.

        Returns the parsed JSON response body.
        Raises httpx.HTTPError on second failure (caller decides partial vs fatal).
        """
        client = await self._get_client()
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                response = await client.get(path, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt == 0:
                    logger.warning("Transient error from %s%s: %s — retrying", self.base_url, path, exc)
                    await asyncio.sleep(1)
        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "BaseCollector":
        await self._get_client()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
