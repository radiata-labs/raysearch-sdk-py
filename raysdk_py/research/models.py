from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from raysdk_py.monitors.types import BaseRequest, BaseResponse
from raysdk_py.utils import clean_whitespace, validate_json_schema

ResearchSearchMode = Literal["research-fast", "research", "research-pro"]
ResearchTaskStatus = Literal["pending", "running", "completed", "canceled", "failed"]


class ResearchRequest(BaseRequest):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    search_mode: ResearchSearchMode = "research"
    themes: str
    json_schema: dict[str, Any] | None = None

    @field_validator("themes")
    @classmethod
    def _validate_themes(cls, value: str) -> str:
        themes = clean_whitespace(str(value or ""))
        if not themes:
            raise ValueError("themes must not be empty")
        return themes

    @field_validator("json_schema")
    @classmethod
    def _validate_schema(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_json_schema(value)


class ResearchResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    content: str
    structured: Any | None = None


class ResearchTaskResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    research_id: str
    create_at: int
    themes: str
    search_mode: ResearchSearchMode
    json_schema: dict[str, Any] | None = None
    status: ResearchTaskStatus
    output: ResearchResponse | None = None
    finished_at: int | None = None
    error: str | None = None


class ResearchTaskListResponse(BaseResponse):
    data: list[ResearchTaskResponse] = Field(default_factory=list)
    has_more: bool
    next_cursor: str = ""


__all__ = [
    "ResearchRequest",
    "ResearchResponse",
    "ResearchSearchMode",
    "ResearchTaskListResponse",
    "ResearchTaskResponse",
    "ResearchTaskStatus",
]
