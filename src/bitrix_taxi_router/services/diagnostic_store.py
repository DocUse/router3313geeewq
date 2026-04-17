from __future__ import annotations

from collections.abc import Callable

from ..database import Database, to_json
from .common import as_optional_str


def record_diagnostic_log(
    database: Database,
    *,
    source: str,
    message: str,
    level: str = "info",
    portal_member_id: str | None = None,
    deal_id: str | None = None,
    details: dict[str, object] | None = None,
    now_factory: Callable[[], str],
) -> None:
    normalized_portal_member_id = as_optional_str(portal_member_id)
    if normalized_portal_member_id:
        existing_portal = database.fetch_one(
            "SELECT member_id FROM portals WHERE member_id = ?",
            (normalized_portal_member_id,),
        )
        if existing_portal is None:
            normalized_portal_member_id = None
    database.execute(
        """
        INSERT INTO diagnostic_logs (
            portal_member_id, deal_id, level, source, message, details_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            normalized_portal_member_id,
            as_optional_str(deal_id),
            level.strip().lower() or "info",
            source.strip(),
            message.strip(),
            to_json(details or {}),
            now_factory(),
        ),
    )
