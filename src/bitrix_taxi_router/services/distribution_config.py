from __future__ import annotations

from typing import Any

from .common import coerce_int


def normalize_distribution_group_payload(payload: dict[str, Any]) -> dict[str, object]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Distribution group name is required")

    distribution_type = str(payload.get("distribution_type") or "").strip()
    if distribution_type != "round_robin_load_time":
        raise ValueError("Unsupported distribution type")

    event_type = str(payload.get("event_type") or "").strip()
    if event_type != "deal_created":
        raise ValueError("Unsupported event type")

    distribution_stage_id = str(payload.get("distribution_stage_id") or "").strip()
    if not distribution_stage_id:
        raise ValueError("Distribution stage is required")

    responsible_field_id = str(payload.get("responsible_field_id") or "").strip()
    if not responsible_field_id:
        raise ValueError("Responsible field is required")

    wait_seconds = coerce_int(payload.get("wait_seconds"), field_name="Wait time")
    retry_interval_seconds = coerce_int(
        payload.get("retry_interval_seconds"),
        field_name="Retry interval",
    )
    if wait_seconds < 1:
        raise ValueError("Wait time must be at least 1 second")
    if retry_interval_seconds < 1:
        raise ValueError("Retry interval must be at least 1 second")

    raw_load_stage_ids = payload.get("load_stage_ids")
    if not isinstance(raw_load_stage_ids, list):
        raise ValueError("Load stages must be a list")
    load_stage_ids = normalize_string_list(raw_load_stage_ids)
    if not load_stage_ids:
        raise ValueError("At least one load stage is required")

    raw_members = payload.get("members")
    if not isinstance(raw_members, list):
        raise ValueError("Distribution members must be a list")

    members: list[dict[str, object]] = []
    seen_user_ids: set[str] = set()
    for index, member in enumerate(raw_members):
        if not isinstance(member, dict):
            raise ValueError("Each distribution member must be an object")
        user_id = str(member.get("user_id") or "").strip()
        if not user_id:
            raise ValueError("Each selected member must have a user_id")
        if user_id in seen_user_ids:
            raise ValueError("Duplicate distribution member detected")
        limit_value = coerce_int(member.get("limit"), field_name=f"Member limit for {user_id}")
        if limit_value < 0:
            raise ValueError("Member limit cannot be negative")
        members.append({"user_id": user_id, "limit": limit_value, "sort_order": index})
        seen_user_ids.add(user_id)

    if not members:
        raise ValueError("At least one distribution member is required")

    return {
        "name": name,
        "distribution_type": distribution_type,
        "event_type": event_type,
        "distribution_stage_id": distribution_stage_id,
        "responsible_field_id": responsible_field_id,
        "wait_seconds": wait_seconds,
        "retry_interval_seconds": retry_interval_seconds,
        "is_active": bool(payload.get("is_active", True)),
        "members": members,
        "load_stage_ids": load_stage_ids,
    }
def normalize_string_list(values: list[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result
