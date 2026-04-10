"""Utility helpers shared across the RaySearch SDK."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

_ISO8601_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WS_RE = re.compile(r"\s+")


def clean_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", (text or "")).strip()


def stable_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def is_iso8601_date_only(value: str) -> bool:
    return _ISO8601_DATE_ONLY_RE.fullmatch(clean_whitespace(value)) is not None


def parse_iso8601_datetime(value: str) -> datetime | None:
    token = clean_whitespace(value)
    if not token:
        return None

    normalized = token
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        if is_iso8601_date_only(normalized):
            parsed = datetime.fromisoformat(f"{normalized}T00:00:00")
        else:
            parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_iso8601_string(value: str, *, allow_blank: bool = False) -> str:
    token = clean_whitespace(value)
    if not token:
        if allow_blank:
            return ""
        raise ValueError("value must not be empty")

    parsed = parse_iso8601_datetime(token)
    if parsed is None:
        raise ValueError("value must be a valid ISO 8601 string")

    if is_iso8601_date_only(token):
        return parsed.date().isoformat()
    return parsed.isoformat()


def normalize_base_url(base_url: str) -> str:
    token = clean_whitespace(base_url)
    if not token:
        raise ValueError("base_url must not be empty")
    return token.rstrip("/")


def validate_json_schema(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
    except Exception as exc:  # noqa: BLE001
        raise ValueError("jsonschema dependency is required") from exc
    Draft202012Validator.check_schema(value)
    return value


__all__ = [
    "clean_whitespace",
    "is_iso8601_date_only",
    "normalize_base_url",
    "normalize_iso8601_string",
    "parse_iso8601_datetime",
    "stable_json",
    "validate_json_schema",
]
