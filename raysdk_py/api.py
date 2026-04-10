from __future__ import annotations

import importlib.metadata
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .utils import normalize_base_url

if TYPE_CHECKING:
    from .monitors import AsyncMonitorsClient, MonitorsClient
    from .monitors.types import (
        AnswerResponse,
        FetchResponse,
        HealthResponse,
        SearchFetchRequest,
        SearchResponse,
    )
    from .research import AsyncResearchClient, ResearchClient

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30.0

ModelT = TypeVar("ModelT", bound=BaseModel)


def _get_package_version() -> str:
    try:
        return importlib.metadata.version("raysdk-py")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


DEFAULT_USER_AGENT = f"raysdk-py/{_get_package_version()}"


class RaySDKError(Exception):
    """Base exception for the SDK."""


class APIConnectionError(RaySDKError):
    """Raised when the service cannot be reached."""


class APITimeoutError(RaySDKError):
    """Raised when a request exceeds the configured timeout."""


class APIStatusError(RaySDKError):
    """Raised when the API returns a non-success status code."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        url: str,
        payload: object | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.url = url
        self.payload = payload
        super().__init__(f"API request failed with status {status_code}: {detail}")


class APIResponseValidationError(RaySDKError):
    """Raised when an API response does not match the expected schema."""

    def __init__(
        self,
        *,
        model_name: str,
        payload: object,
        cause: ValidationError,
    ) -> None:
        self.model_name = model_name
        self.payload = payload
        self.cause = cause
        super().__init__(f"failed to validate response as {model_name}: {cause}")


def _resolve_api_key(api_key: str | None) -> str:
    token = api_key or os.environ.get("RAYSEARCH_API_KEY")
    if token is None or not token.strip():
        raise ValueError(
            "API key must be provided as an argument or in RAYSEARCH_API_KEY."
        )
    return token


def _merge_headers(
    *,
    api_key: str,
    default_headers: Mapping[str, str] | None,
    user_agent: str,
) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": user_agent,
    }
    if default_headers:
        headers.update(default_headers)
    return headers


def _extract_error_detail(response: httpx.Response) -> tuple[str, object | None]:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text or response.reason_phrase, None

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail, payload
    return response.reason_phrase, payload


def validate_response_model(model_type: type[ModelT], payload: object) -> ModelT:
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise APIResponseValidationError(
            model_name=model_type.__name__,
            payload=payload,
            cause=exc,
        ) from exc


def serialize_request_model(
    model_type: type[ModelT],
    payload: ModelT | Mapping[str, Any],
) -> dict[str, Any]:
    model = (
        payload
        if isinstance(payload, model_type)
        else model_type.model_validate(payload)
    )
    return model.model_dump(mode="json", exclude_none=True)


def _raise_non_json_error(response: httpx.Response, exc: ValueError) -> None:
    try:
        raise ValidationError.from_exception_data(
            title="JSON",
            line_errors=[],
        )
    except ValidationError as validation_error:
        raise APIResponseValidationError(
            model_name="JSON",
            payload=response.text,
            cause=validation_error,
        ) from exc


class SyncAPIClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
        default_headers: Mapping[str, str] | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        resolved_api_key = _resolve_api_key(api_key)
        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.headers = _merge_headers(
            api_key=resolved_api_key,
            default_headers=default_headers,
            user_agent=user_agent,
        )
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> SyncAPIClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb
        self.close()

    def _url_for(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def request(
        self,
        endpoint: str,
        data: Mapping[str, Any] | str | None = None,
        method: str = "POST",
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> object:
        url = self._url_for(endpoint)
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)

        try:
            if isinstance(data, str):
                response = self._client.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                    content=data,
                )
            elif data is not None:
                response = self._client.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                    json=data,
                )
            else:
                response = self._client.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                )
        except httpx.TimeoutException as exc:
            raise APITimeoutError(f"request timed out for {url}") from exc
        except httpx.HTTPError as exc:
            raise APIConnectionError(f"request failed for {url}") from exc

        if response.is_error:
            detail, payload = _extract_error_detail(response)
            raise APIStatusError(
                status_code=response.status_code,
                detail=detail,
                url=str(response.request.url),
                payload=payload,
            )

        try:
            return response.json()
        except ValueError as exc:
            _raise_non_json_error(response, exc)

    def request_model(
        self,
        model_type: type[ModelT],
        endpoint: str,
        *,
        data: Mapping[str, Any] | str | None = None,
        method: str = "POST",
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ModelT:
        payload = self.request(
            endpoint,
            data=data,
            method=method,
            params=params,
            headers=headers,
        )
        return validate_response_model(model_type, payload)


class AsyncAPIClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
        default_headers: Mapping[str, str] | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        resolved_api_key = _resolve_api_key(api_key)
        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.headers = _merge_headers(
            api_key=resolved_api_key,
            default_headers=default_headers,
            user_agent=user_agent,
        )
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncAPIClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb
        await self.aclose()

    def _url_for(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def async_request(
        self,
        endpoint: str,
        data: Mapping[str, Any] | str | None = None,
        method: str = "POST",
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> object:
        url = self._url_for(endpoint)
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)

        try:
            if isinstance(data, str):
                response = await self._client.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                    content=data,
                )
            elif data is not None:
                response = await self._client.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                    json=data,
                )
            else:
                response = await self._client.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                )
        except httpx.TimeoutException as exc:
            raise APITimeoutError(f"request timed out for {url}") from exc
        except httpx.HTTPError as exc:
            raise APIConnectionError(f"request failed for {url}") from exc

        if response.is_error:
            detail, payload = _extract_error_detail(response)
            raise APIStatusError(
                status_code=response.status_code,
                detail=detail,
                url=str(response.request.url),
                payload=payload,
            )

        try:
            return response.json()
        except ValueError as exc:
            _raise_non_json_error(response, exc)

    async def request_model(
        self,
        model_type: type[ModelT],
        endpoint: str,
        *,
        data: Mapping[str, Any] | str | None = None,
        method: str = "POST",
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ModelT:
        payload = await self.async_request(
            endpoint,
            data=data,
            method=method,
            params=params,
            headers=headers,
        )
        return validate_response_model(model_type, payload)


class RaySearch(SyncAPIClient):
    """Top-level synchronous client for the RaySearch API."""

    monitors: MonitorsClient
    research: ResearchClient

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str | None = None,
        client: httpx.Client | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            client=client,
            default_headers=default_headers,
            user_agent=user_agent or DEFAULT_USER_AGENT,
        )

        from .monitors import MonitorsClient
        from .research import ResearchClient

        self.monitors = MonitorsClient(self)
        self.research = ResearchClient(self)

    def healthz(self) -> HealthResponse:
        return self.monitors.healthz()

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
        return self.monitors.search(
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
        return self.monitors.fetch(
            urls,
            crawl_mode=crawl_mode,
            crawl_timeout=crawl_timeout,
            content=content,
            abstracts=abstracts,
            subpages=subpages,
            overview=overview,
            others=others,
        )

    def answer(
        self,
        query: str,
        *,
        json_schema: dict[str, Any] | None = None,
        content: bool = False,
    ) -> AnswerResponse:
        return self.monitors.answer(
            query,
            json_schema=json_schema,
            content=content,
        )


class AsyncRaySearch(AsyncAPIClient):
    """Top-level asynchronous client for the RaySearch API."""

    monitors: AsyncMonitorsClient
    research: AsyncResearchClient

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str | None = None,
        client: httpx.AsyncClient | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            client=client,
            default_headers=default_headers,
            user_agent=user_agent or DEFAULT_USER_AGENT,
        )

        from .monitors import AsyncMonitorsClient
        from .research import AsyncResearchClient

        self.monitors = AsyncMonitorsClient(self)
        self.research = AsyncResearchClient(self)

    async def healthz(self) -> HealthResponse:
        return await self.monitors.healthz()

    async def search(
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
        return await self.monitors.search(
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

    async def fetch(
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
        return await self.monitors.fetch(
            urls,
            crawl_mode=crawl_mode,
            crawl_timeout=crawl_timeout,
            content=content,
            abstracts=abstracts,
            subpages=subpages,
            overview=overview,
            others=others,
        )

    async def answer(
        self,
        query: str,
        *,
        json_schema: dict[str, Any] | None = None,
        content: bool = False,
    ) -> AnswerResponse:
        return await self.monitors.answer(
            query,
            json_schema=json_schema,
            content=content,
        )


__all__ = [
    "APIConnectionError",
    "APIResponseValidationError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncAPIClient",
    "AsyncRaySearch",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENT",
    "RaySDKError",
    "RaySearch",
    "SyncAPIClient",
    "serialize_request_model",
    "validate_response_model",
]
