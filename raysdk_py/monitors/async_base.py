"""Base async client classes for the RaySearch monitor-style endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..api import AsyncRaySearch


class AsyncMonitorsBaseClient:
    """Base client for asynchronous monitor-style API operations."""

    def __init__(self, client: AsyncRaySearch) -> None:
        self._client = client

    async def request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Mapping[str, Any] | str | None = None,
        params: dict[str, str | int] | None = None,
    ) -> object:
        return await self._client.async_request(
            endpoint,
            data=data,
            method=method,
            params=params,
        )


__all__ = ["AsyncMonitorsBaseClient"]
