"""Asynchronous Research API client."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from ..api import serialize_request_model
from .base import AsyncResearchBaseClient
from .models import ResearchRequest, ResearchTaskListResponse, ResearchTaskResponse


class AsyncResearchClient(AsyncResearchBaseClient):
    """Asynchronous client for the research task endpoints."""

    async def create(
        self,
        *,
        themes: str,
        search_mode: str = "research",
        json_schema: dict[str, object] | None = None,
    ) -> ResearchTaskResponse:
        payload = self.build_create_request(
            themes,
            search_mode=search_mode,
            json_schema=json_schema,
        )
        response = await self.request(
            "",
            method="POST",
            data=serialize_request_model(ResearchRequest, payload),
        )
        return ResearchTaskResponse.model_validate(response)

    async def get(self, research_id: str) -> ResearchTaskResponse:
        response = await self.request(
            f"/{self.normalize_research_id(research_id)}",
            method="GET",
        )
        return ResearchTaskResponse.model_validate(response)

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> ResearchTaskListResponse:
        response = await self.request(
            "",
            method="GET",
            params=self.build_pagination_params(cursor, limit),
        )
        return ResearchTaskListResponse.model_validate(response)

    async def cancel(self, research_id: str) -> ResearchTaskResponse:
        response = await self.request(
            f"/{self.normalize_research_id(research_id)}",
            method="DELETE",
        )
        return ResearchTaskResponse.model_validate(response)

    async def list_all(
        self,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[ResearchTaskResponse]:
        cursor: str | None = None
        while True:
            response = await self.list(cursor=cursor, limit=limit)
            for task in response.data:
                yield task
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    async def get_all(self, *, limit: int | None = None) -> list[ResearchTaskResponse]:
        items: list[ResearchTaskResponse] = []
        async for task in self.list_all(limit=limit):
            items.append(task)
        return items

    async def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
    ) -> ResearchTaskResponse:
        poll_interval_sec = poll_interval / 1000
        timeout_sec = timeout_ms / 1000
        start_time = asyncio.get_running_loop().time()
        consecutive_failures = 0
        max_consecutive_failures = 5

        while True:
            try:
                result = await self.get(research_id)
                consecutive_failures = 0
                if result.status in {"completed", "failed", "canceled"}:
                    return result
            except Exception as exc:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    raise RuntimeError(
                        f"Polling failed {max_consecutive_failures} times in a row "
                        f"for research {research_id}: {exc}"
                    ) from exc

            if asyncio.get_running_loop().time() - start_time > timeout_sec:
                raise TimeoutError(
                    f"Research {research_id} did not complete within {timeout_ms}ms"
                )

            await asyncio.sleep(poll_interval_sec)


__all__ = ["AsyncResearchClient"]
