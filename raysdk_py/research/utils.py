from __future__ import annotations

from collections.abc import Mapping

from raysdk_py.utils import clean_whitespace


def normalize_research_id(research_id: str) -> str:
    token = clean_whitespace(research_id)
    if not token:
        raise ValueError("research_id must not be empty")
    return token


def build_list_params(
    *,
    cursor: str | None = None,
    limit: int | None = None,
) -> Mapping[str, str | int] | None:
    params: dict[str, str | int] = {}

    cursor_token = clean_whitespace(str(cursor or ""))
    if cursor_token:
        params["cursor"] = cursor_token

    if limit is not None:
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        params["limit"] = limit

    return params or None


__all__ = ["build_list_params", "normalize_research_id"]
