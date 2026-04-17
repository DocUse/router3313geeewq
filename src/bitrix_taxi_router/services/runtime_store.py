from __future__ import annotations

from collections.abc import Callable

from ..database import Database
from .common import as_optional_str


def get_member_last_assigned_map(database: Database, portal_member_id: str) -> dict[str, str | None]:
    rows = database.fetch_all(
        """
        SELECT user_id, last_assigned_at
        FROM distribution_member_runtime
        WHERE portal_member_id = ?
        """,
        (portal_member_id,),
    )
    return {str(row["user_id"]): as_optional_str(row["last_assigned_at"]) for row in rows}


def touch_member_runtime(
    database: Database,
    portal_member_id: str,
    user_id: str,
    deal_id: str,
    *,
    now_factory: Callable[[], str],
) -> None:
    now = now_factory()
    with database.connection() as connection:
        connection.execute(
            """
            INSERT INTO distribution_member_runtime (
                portal_member_id, user_id, last_assigned_deal_id, last_assigned_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(portal_member_id, user_id) DO UPDATE SET
                last_assigned_deal_id = excluded.last_assigned_deal_id,
                last_assigned_at = excluded.last_assigned_at,
                updated_at = excluded.updated_at
            """,
            (portal_member_id, user_id, deal_id, now, now),
        )


def get_deal_runtime(
    database: Database,
    portal_member_id: str,
    deal_id: str,
    event_type: str,
) -> dict[str, object] | None:
    row = database.fetch_one(
        """
        SELECT *
        FROM distribution_deal_runtime
        WHERE portal_member_id = ? AND deal_id = ? AND event_type = ?
        """,
        (portal_member_id, deal_id, event_type),
    )
    if row is None:
        return None
    return {
        "portal_member_id": str(row["portal_member_id"]),
        "deal_id": str(row["deal_id"]),
        "event_type": str(row["event_type"]),
        "status": str(row["status"]),
        "assigned_user_id": as_optional_str(row["assigned_user_id"]),
        "assigned_field_id": as_optional_str(row["assigned_field_id"]),
        "note": as_optional_str(row["note"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def record_and_return_deal_runtime(
    database: Database,
    portal_member_id: str,
    deal_id: str,
    *,
    event_type: str,
    status: str,
    note: str,
    assigned_user_id: str | None = None,
    assigned_field_id: str | None = None,
    extra: dict[str, object] | None = None,
    now_factory: Callable[[], str],
) -> dict[str, object]:
    now = now_factory()
    existing = get_deal_runtime(database, portal_member_id, deal_id, event_type)
    created_at = str(existing["created_at"]) if existing is not None else now

    with database.connection() as connection:
        connection.execute(
            """
            INSERT INTO distribution_deal_runtime (
                portal_member_id, deal_id, event_type, status, assigned_user_id,
                assigned_field_id, note, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(portal_member_id, deal_id, event_type) DO UPDATE SET
                status = excluded.status,
                assigned_user_id = excluded.assigned_user_id,
                assigned_field_id = excluded.assigned_field_id,
                note = excluded.note,
                updated_at = excluded.updated_at
            """,
            (
                portal_member_id,
                deal_id,
                event_type,
                status,
                assigned_user_id,
                assigned_field_id,
                note,
                created_at,
                now,
            ),
        )

    result = get_deal_runtime(database, portal_member_id, deal_id, event_type)
    if result is None:
        raise ValueError("Distribution deal runtime was not saved")
    if extra:
        result.update(extra)
    return result
