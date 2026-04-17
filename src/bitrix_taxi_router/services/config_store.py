from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from ..database import Database, to_json
from .distribution_config import normalize_distribution_group_payload


def get_distribution_group(
    database: Database,
    portal_member_id: str,
    *,
    ensure_portal_exists: Callable[[str], object],
) -> dict[str, object] | None:
    ensure_portal_exists(portal_member_id)
    row = database.fetch_one(
        "SELECT * FROM distribution_group_configs WHERE portal_member_id = ?",
        (portal_member_id,),
    )
    if row is None:
        return None

    members = parse_json_list(row["members_json"], "distribution group members")
    load_stage_ids = parse_json_list(row["load_stage_ids_json"], "distribution load stages")
    return {
        "portal_member_id": str(row["portal_member_id"]),
        "name": str(row["name"]),
        "distribution_type": str(row["distribution_type"]),
        "event_type": str(row["event_type"]),
        "distribution_stage_id": str(row["distribution_stage_id"]),
        "responsible_field_id": str(row["responsible_field_id"]),
        "wait_seconds": int(row["wait_seconds"]),
        "retry_interval_seconds": int(row["retry_interval_seconds"]),
        "is_active": bool(int(row["is_active"])),
        "members": members,
        "load_stage_ids": load_stage_ids,
    }


def save_distribution_group(
    database: Database,
    portal_member_id: str,
    payload: dict[str, Any],
    *,
    ensure_portal_exists: Callable[[str], object],
    load_distribution_group: Callable[[str], dict[str, object] | None],
    now_factory: Callable[[], str],
) -> dict[str, object]:
    ensure_portal_exists(portal_member_id)
    normalized = normalize_distribution_group_payload(payload)
    now = now_factory()

    with database.connection() as connection:
        connection.execute(
            """
            INSERT INTO distribution_group_configs (
                portal_member_id, name, distribution_type, event_type, distribution_stage_id,
                responsible_field_id, wait_seconds, retry_interval_seconds, is_active,
                members_json, load_stage_ids_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(portal_member_id) DO UPDATE SET
                name = excluded.name,
                distribution_type = excluded.distribution_type,
                event_type = excluded.event_type,
                distribution_stage_id = excluded.distribution_stage_id,
                responsible_field_id = excluded.responsible_field_id,
                wait_seconds = excluded.wait_seconds,
                retry_interval_seconds = excluded.retry_interval_seconds,
                is_active = excluded.is_active,
                members_json = excluded.members_json,
                load_stage_ids_json = excluded.load_stage_ids_json,
                updated_at = excluded.updated_at
            """,
            (
                portal_member_id,
                normalized["name"],
                normalized["distribution_type"],
                normalized["event_type"],
                normalized["distribution_stage_id"],
                normalized["responsible_field_id"],
                normalized["wait_seconds"],
                normalized["retry_interval_seconds"],
                1 if bool(normalized["is_active"]) else 0,
                to_json(normalized["members"]),
                to_json(normalized["load_stage_ids"]),
                now,
                now,
            ),
        )

    saved = load_distribution_group(portal_member_id)
    if saved is None:
        raise ValueError("Distribution group was not saved")
    return saved


def parse_json_list(raw_value: Any, field_name: str) -> list[dict[str, object]] | list[str]:
    try:
        parsed = json.loads(str(raw_value or "[]"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Stored {field_name} payload is invalid") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"Stored {field_name} payload must be a list")
    return parsed


def parse_json_object(raw_value: Any, field_name: str) -> dict[str, object]:
    try:
        parsed = json.loads(str(raw_value or "{}"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Stored {field_name} payload is invalid") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"Stored {field_name} payload must be an object")
    return parsed
