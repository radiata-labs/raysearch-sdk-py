"""Synchronous client for the RaySearch monitor-style endpoints."""

from __future__ import annotations

from typing import Any

from ..api import serialize_request_model
from .base import MonitorsBaseClient
from .types import (
    AnswerRequest,
    AnswerResponse,
    FetchRequest,
    FetchResponse,
    HealthResponse,
    SearchFetchRequest,
    SearchRequest,
    SearchResponse,
)


class MonitorsClient(MonitorsBaseClient):
    """Synchronous client for search, fetch, answer, and health operations."""

    def healthz(self) -> HealthResponse:
        response = self.request("/healthz", method="GET")
        return HealthResponse.model_validate(response)

    def search(
        self,
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
    ) -> SearchResponse:
        payload = self.build_search_request(
            query,
            user_location=user_location,
            additional_queries=additional_queries,
            mode=mode,
            max_results=max_results,
            start_published_date=start_published_date,
            end_published_date=end_published_date,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_text=include_text,
            exclude_text=exclude_text,
            moderation=moderation,
            fetchs=fetchs,
        )
        response = self.request(
            "/v1/search",
            data=serialize_request_model(SearchRequest, payload),
            method="POST",
        )
        return SearchResponse.model_validate(response)

    def fetch(
        self,
        urls: str | list[str],
        *,
        crawl_mode: str = "fallback",
        crawl_timeout: float | None = None,
        content: bool | dict[str, Any] = False,
        abstracts: bool | dict[str, Any] = False,
        subpages: dict[str, Any] | None = None,
        overview: bool | dict[str, Any] = False,
        others: dict[str, Any] | None = None,
    ) -> FetchResponse:
        payload = self.build_fetch_request(
            urls,
            crawl_mode=crawl_mode,
            crawl_timeout=crawl_timeout,
            content=content,
            abstracts=abstracts,
            subpages=subpages,
            overview=overview,
            others=others,
        )
        response = self.request(
            "/v1/fetch",
            data=serialize_request_model(FetchRequest, payload),
            method="POST",
        )
        return FetchResponse.model_validate(response)

    def answer(
        self,
        query: str,
        *,
        json_schema: dict[str, Any] | None = None,
        content: bool = False,
    ) -> AnswerResponse:
        payload = self.build_answer_request(
            query,
            json_schema=json_schema,
            content=content,
        )
        response = self.request(
            "/v1/answer",
            data=serialize_request_model(AnswerRequest, payload),
            method="POST",
        )
        return AnswerResponse.model_validate(response)


__all__ = ["MonitorsClient"]
