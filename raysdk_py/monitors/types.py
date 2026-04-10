from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from raysdk_py.utils import (
    clean_whitespace,
    normalize_iso8601_string,
    parse_iso8601_datetime,
    validate_json_schema,
)

SearchMode = Literal["fast", "auto", "deep"]
FetchContentDetail = Literal["concise", "standard", "full"]
FetchContentTag = Literal[
    "header",
    "navigation",
    "banner",
    "body",
    "sidebar",
    "footer",
    "metadata",
]
CrawlMode = Literal["never", "fallback", "preferred", "always"]
FetchErrorTag = Literal[
    "CRAWL_NOT_FOUND",
    "CRAWL_TIMEOUT",
    "CRAWL_LIVECRAWL_TIMEOUT",
    "SOURCE_NOT_AVAILABLE",
    "UNSUPPORTED_URL",
    "CRAWL_UNKNOWN_ERROR",
]

_LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_CJK_CHAR_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff]")
_ISO_COUNTRY_CODE_RE = re.compile(r"^[A-Za-z]{2}$")


class BaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class BaseResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True)


def _normalize_domain(value: str) -> str:
    text = clean_whitespace(value).lower().strip(".")
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("/", 1)[0].split(":", 1)[0].strip()
    return text.removeprefix("www.")


def _normalize_string_list(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None

    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = clean_whitespace(str(raw or ""))
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out or None


def _validate_text_phrase_limit(value: str) -> None:
    cleaned = clean_whitespace(value)
    cjk_count = len(_CJK_CHAR_RE.findall(cleaned))
    word_count = len([token for token in cleaned.split(" ") if token])
    latin_word_count = len(_LATIN_WORD_RE.findall(cleaned))

    if cjk_count > 0 and latin_word_count <= 1:
        if cjk_count > 6:
            raise ValueError(
                "each text filter phrase supports at most 6 Chinese/Japanese characters"
            )
        return

    if word_count > 5:
        raise ValueError("each text filter phrase supports at most 5 words")


def _normalize_iso_country_code(value: str, *, field_name: str) -> str:
    token = clean_whitespace(str(value or "")).upper()
    if not _ISO_COUNTRY_CODE_RE.fullmatch(token):
        raise ValueError(f"{field_name} must be a two-letter ISO country code")
    return token


class HealthResponse(BaseResponse):
    status: Literal["ok", "error"]
    engine_ready: bool


class FetchOthersRequest(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    max_links: int | None = None
    max_image_links: int | None = None

    @field_validator("max_links", "max_image_links")
    @classmethod
    def _validate_positive_limit(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("limit must be > 0")
        return value


class FetchContentRequest(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    max_chars: int | None = None
    detail: FetchContentDetail = "concise"
    include_markdown_links: bool = False
    include_html_tags: bool = False
    include_tags: list[FetchContentTag] = Field(default_factory=list)
    exclude_tags: list[FetchContentTag] = Field(default_factory=list)

    @field_validator("max_chars")
    @classmethod
    def _validate_max_chars(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("max_chars must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_tag_overlap(self) -> FetchContentRequest:
        overlap = sorted(set(self.include_tags) & set(self.exclude_tags))
        if overlap:
            raise ValueError(
                "include_tags and exclude_tags must not overlap: " + ", ".join(overlap)
            )
        return self


class FetchAbstractsRequest(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    query: str | None = None
    max_chars: int | None = None

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str | None) -> str | None:
        query = str(value or "").strip()
        return query or None

    @field_validator("max_chars")
    @classmethod
    def _validate_positive_int(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("value must be > 0")
        return value


class FetchOverviewRequest(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    query: str | None = None
    json_schema: dict[str, Any] | None = None

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str | None) -> str | None:
        query = str(value or "").strip()
        return query or None

    @field_validator("json_schema")
    @classmethod
    def _validate_schema(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_json_schema(value)


class FetchSubpagesRequest(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    max_subpages: int | None = None
    subpage_keywords: str | list[str] | None = None

    @field_validator("max_subpages")
    @classmethod
    def _validate_max_subpages(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("max_subpages must be > 0")
        return value

    @field_validator("subpage_keywords", mode="before")
    @classmethod
    def _validate_subpage_keywords(
        cls,
        value: str | list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, list):
            cleaned = [clean_whitespace(str(item)) for item in value]
            return [item for item in cleaned if item] or None

        text = clean_whitespace(str(value)).replace("\uff0c", ",")
        if not text:
            return None

        out: list[str] = []
        seen: set[str] = set()
        for raw in text.split(","):
            token = clean_whitespace(raw)
            if not token or token in seen:
                continue
            seen.add(token)
            out.append(token)
        return out or None


class SearchFetchRequest(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    crawl_mode: CrawlMode = "fallback"
    crawl_timeout: float | None = None
    content: bool | FetchContentRequest = False
    abstracts: bool | FetchAbstractsRequest = False
    subpages: FetchSubpagesRequest | None = None
    overview: bool | FetchOverviewRequest = False
    others: FetchOthersRequest | None = None

    @field_validator("crawl_timeout")
    @classmethod
    def _validate_crawl_timeout(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("crawl_timeout must be > 0")
        return float(value)

    @model_validator(mode="after")
    def _validate_has_action(self) -> SearchFetchRequest:
        content_enabled = not isinstance(self.content, bool) or self.content
        abstracts_enabled = not isinstance(self.abstracts, bool) or self.abstracts
        overview_enabled = not isinstance(self.overview, bool) or self.overview
        subpages_enabled = self.subpages is not None
        others_enabled = self.others is not None and (
            self.others.max_links is not None or self.others.max_image_links is not None
        )

        if not (
            content_enabled
            or abstracts_enabled
            or overview_enabled
            or subpages_enabled
            or others_enabled
        ):
            raise ValueError(
                "fetch request has nothing to do: enable at least one of "
                "content/abstracts/overview/subpages/others"
            )
        return self


class SearchRequest(BaseRequest):
    query: str
    user_location: str
    additional_queries: list[str] | None = None
    mode: SearchMode = "auto"
    max_results: int | None = None
    start_published_date: str | None = None
    end_published_date: str | None = None
    include_domains: list[str] | None = None
    exclude_domains: list[str] | None = None
    include_text: list[str] | None = None
    exclude_text: list[str] | None = None
    moderation: bool = True
    fetchs: SearchFetchRequest

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        query = clean_whitespace(str(value or ""))
        if not query:
            raise ValueError("query must not be empty")
        return query

    @field_validator("user_location")
    @classmethod
    def _validate_user_location(cls, value: str) -> str:
        return _normalize_iso_country_code(value, field_name="user_location")

    @field_validator("additional_queries")
    @classmethod
    def _validate_additional_queries(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_string_list(value)

    @field_validator("start_published_date", "end_published_date")
    @classmethod
    def _validate_published_date_bounds(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_iso8601_string(value)

    @field_validator("include_domains", "exclude_domains")
    @classmethod
    def _validate_domains(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None

        out: list[str] = []
        seen: set[str] = set()
        for raw in value:
            domain = _normalize_domain(str(raw or ""))
            if not domain or domain in seen:
                continue
            seen.add(domain)
            out.append(domain)
        return out or None

    @field_validator("include_text", "exclude_text")
    @classmethod
    def _validate_text_filters(cls, value: list[str] | None) -> list[str] | None:
        normalized = _normalize_string_list(value)
        if normalized is None:
            return None
        for item in normalized:
            _validate_text_phrase_limit(item)
        return normalized

    @field_validator("max_results")
    @classmethod
    def _validate_max_results(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("max_results must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_search_request(self) -> SearchRequest:
        if self.mode != "deep" and self.additional_queries:
            raise ValueError("additional_queries is only supported when mode=deep")

        include_set = set(self.include_domains or [])
        exclude_set = set(self.exclude_domains or [])
        overlap = sorted(include_set & exclude_set)
        if overlap:
            raise ValueError(
                "include_domains and exclude_domains must not overlap: "
                + ", ".join(overlap)
            )

        start_at = parse_iso8601_datetime(str(self.start_published_date or ""))
        end_at = parse_iso8601_datetime(str(self.end_published_date or ""))
        if start_at is not None and end_at is not None and start_at > end_at:
            raise ValueError("start_published_date must be <= end_published_date")
        return self


class FetchRequest(BaseRequest):
    urls: list[str]
    crawl_mode: CrawlMode = "fallback"
    crawl_timeout: float | None = None
    content: bool | FetchContentRequest = False
    abstracts: bool | FetchAbstractsRequest = False
    subpages: FetchSubpagesRequest | None = None
    overview: bool | FetchOverviewRequest = False
    others: FetchOthersRequest | None = None

    @field_validator("crawl_timeout")
    @classmethod
    def _validate_crawl_timeout(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("crawl_timeout must be > 0")
        return float(value)

    @model_validator(mode="after")
    def _validate_has_action(self) -> FetchRequest:
        content_enabled = not isinstance(self.content, bool) or self.content
        abstracts_enabled = not isinstance(self.abstracts, bool) or self.abstracts
        overview_enabled = not isinstance(self.overview, bool) or self.overview
        subpages_enabled = self.subpages is not None
        others_enabled = self.others is not None and (
            self.others.max_links is not None or self.others.max_image_links is not None
        )

        if not (
            content_enabled
            or abstracts_enabled
            or overview_enabled
            or subpages_enabled
            or others_enabled
        ):
            raise ValueError(
                "fetch request has nothing to do: enable at least one of "
                "content/abstracts/overview/subpages/others"
            )
        return self

    @field_validator("urls")
    @classmethod
    def _validate_urls(cls, value: list[str]) -> list[str]:
        out: list[str] = []
        for raw in value:
            url = str(raw or "").strip()
            if not url:
                raise ValueError("urls must not contain empty value")
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"unsupported url scheme: {url}")
            out.append(url)
        if not out:
            raise ValueError("urls must not be empty")
        return out


class AnswerRequest(BaseRequest):
    query: str
    json_schema: dict[str, Any] | None = None
    content: bool = False

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        query = clean_whitespace(str(value or ""))
        if not query:
            raise ValueError("query must not be empty")
        return query

    @field_validator("json_schema")
    @classmethod
    def _validate_schema(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_json_schema(value)


class FetchOthersResult(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    links: list[str] = Field(default_factory=list)
    image_links: list[str] = Field(default_factory=list)


class FetchSubpagesResult(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    url: str
    title: str
    published_date: str = ""
    author: str = ""
    image: str = ""
    favicon: str = ""
    content: str
    abstracts: list[str] = Field(default_factory=list)
    abstract_scores: list[float] = Field(default_factory=list)
    overview: Any | None = None

    @field_validator("published_date")
    @classmethod
    def _validate_published_date(cls, value: str) -> str:
        return normalize_iso8601_string(value, allow_blank=True)

    @model_validator(mode="after")
    def _validate_abstract_alignment(self) -> FetchSubpagesResult:
        if len(self.abstracts) != len(self.abstract_scores):
            raise ValueError("abstracts and abstract_scores length mismatch")
        return self


class FetchResultItem(FetchSubpagesResult):
    subpages: list[FetchSubpagesResult] = Field(default_factory=list)
    others: FetchOthersResult | None = None


class FetchStatusError(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    tag: FetchErrorTag
    detail: str | None = None


class FetchStatusItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    url: str
    status: Literal["success", "error"]
    error: FetchStatusError | None = None


class FetchResponse(BaseResponse):
    request_id: str
    results: list[FetchResultItem] = Field(default_factory=list)
    statuses: list[FetchStatusItem] = Field(default_factory=list)


class SearchResponse(BaseResponse):
    request_id: str
    search_mode: str
    results: list[FetchResultItem] = Field(default_factory=list)


class AnswerCitation(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str
    url: str
    title: str
    content: str | None = None


class AnswerResponse(BaseResponse):
    request_id: str
    answer: Any
    citations: list[AnswerCitation] = Field(default_factory=list)


__all__ = [
    "AnswerCitation",
    "AnswerRequest",
    "AnswerResponse",
    "BaseRequest",
    "BaseResponse",
    "CrawlMode",
    "FetchAbstractsRequest",
    "FetchContentDetail",
    "FetchContentRequest",
    "FetchContentTag",
    "FetchErrorTag",
    "FetchOthersRequest",
    "FetchOthersResult",
    "FetchOverviewRequest",
    "FetchRequest",
    "FetchResponse",
    "FetchResultItem",
    "FetchStatusError",
    "FetchStatusItem",
    "FetchSubpagesRequest",
    "FetchSubpagesResult",
    "HealthResponse",
    "SearchFetchRequest",
    "SearchMode",
    "SearchRequest",
    "SearchResponse",
]
