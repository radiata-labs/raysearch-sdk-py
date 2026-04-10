"""Base client classes for the RaySearch research API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .models import ResearchRequest
from .utils import build_list_params, normalize_research_id

if TYPE_CHECKING:
    from ..api import AsyncRaySearch, RaySearch


class ResearchBaseClient:
    """Base client for synchronous research API operations."""

    def __init__(self, client: RaySearch) -> None:
        self._client = client
        self.base_path = "/v1/research"

    def request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Mapping[str, Any] | str | None = None,
        params: dict[str, str | int] | None = None,
    ) -> object:
        return self._client.request(
            f"{self.base_path}{endpoint}",
            data=data,
            method=method,
            params=params,
        )

    def build_pagination_params(
        self,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, str | int]:
        params = build_list_params(cursor=cursor, limit=limit)
        return dict(params) if params is not None else {}

    @staticmethod
    def build_create_request(
        themes: str,
        *,
        search_mode: str = "research",
        json_schema: dict[str, Any] | None = None,
    ) -> ResearchRequest:
        return ResearchRequest.model_validate(
            {
                "themes": themes,
                "search_mode": search_mode,
                "json_schema": json_schema,
            }
        )

    @staticmethod
    def normalize_research_id(research_id: str) -> str:
        return normalize_research_id(research_id)


class AsyncResearchBaseClient:
    """Base client for asynchronous research API operations."""

    def __init__(self, client: AsyncRaySearch) -> None:
        self._client = client
        self.base_path = "/v1/research"

    async def request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Mapping[str, Any] | str | None = None,
        params: dict[str, str | int] | None = None,
    ) -> object:
        return await self._client.async_request(
            f"{self.base_path}{endpoint}",
            data=data,
            method=method,
            params=params,
        )

    def build_pagination_params(
        self,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, str | int]:
        params = build_list_params(cursor=cursor, limit=limit)
        return dict(params) if params is not None else {}

    @staticmethod
    def build_create_request(
        themes: str,
        *,
        search_mode: str = "research",
        json_schema: dict[str, Any] | None = None,
    ) -> ResearchRequest:
        return ResearchRequest.model_validate(
            {
                "themes": themes,
                "search_mode": search_mode,
                "json_schema": json_schema,
            }
        )

    @staticmethod
    def normalize_research_id(research_id: str) -> str:
        return normalize_research_id(research_id)


__all__ = ["AsyncResearchBaseClient", "ResearchBaseClient"]
