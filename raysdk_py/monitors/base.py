"""Base client classes for the RaySearch monitor-style endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .types import (
    AnswerRequest,
    FetchRequest,
    SearchFetchRequest,
    SearchRequest,
)

if TYPE_CHECKING:
    from ..api import RaySearch


class MonitorsBaseClient:
    """Base client for synchronous search, fetch, and answer operations."""

    def __init__(self, client: RaySearch) -> None:
        self._client = client

    def request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Mapping[str, Any] | str | None = None,
        params: dict[str, str | int] | None = None,
    ) -> object:
        return self._client.request(endpoint, data=data, method=method, params=params)

    @staticmethod
    def build_search_request(
        query: str,
        *,
        user_location: str,
        additional_queries: list[str] | None = None,
        mode: str = "auto",
        max_results: int | None = None,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        include_text: list[str] | None = None,
        exclude_text: list[str] | None = None,
        moderation: bool = True,
        fetchs: SearchFetchRequest | dict[str, Any],
    ) -> SearchRequest:
        return SearchRequest.model_validate(
            {
                "query": query,
                "user_location": user_location,
                "additional_queries": additional_queries,
                "mode": mode,
                "max_results": max_results,
                "start_published_date": start_published_date,
                "end_published_date": end_published_date,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "include_text": include_text,
                "exclude_text": exclude_text,
                "moderation": moderation,
                "fetchs": fetchs,
            }
        )

    @staticmethod
    def build_fetch_request(
        urls: str | list[str],
        *,
        crawl_mode: str = "fallback",
        crawl_timeout: float | None = None,
        content: bool | dict[str, Any] = False,
        abstracts: bool | dict[str, Any] = False,
        subpages: dict[str, Any] | None = None,
        overview: bool | dict[str, Any] = False,
        others: dict[str, Any] | None = None,
    ) -> FetchRequest:
        normalized_urls = [urls] if isinstance(urls, str) else list(urls)
        return FetchRequest.model_validate(
            {
                "urls": normalized_urls,
                "crawl_mode": crawl_mode,
                "crawl_timeout": crawl_timeout,
                "content": content,
                "abstracts": abstracts,
                "subpages": subpages,
                "overview": overview,
                "others": others,
            }
        )

    @staticmethod
    def build_answer_request(
        query: str,
        *,
        json_schema: dict[str, Any] | None = None,
        content: bool = False,
    ) -> AnswerRequest:
        return AnswerRequest.model_validate(
            {
                "query": query,
                "json_schema": json_schema,
                "content": content,
            }
        )


__all__ = ["MonitorsBaseClient"]
