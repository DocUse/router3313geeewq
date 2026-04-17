from __future__ import annotations

from typing import Any


def as_optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def coerce_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def maybe_int(value: Any) -> int | str:
    text = str(value or "").strip()
    if text.isdigit():
        return int(text)
    return text
