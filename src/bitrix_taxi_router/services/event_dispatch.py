from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..database import Database
from .common import as_optional_str
from .deal_processing import BitrixListClient
from .deal_processing import handle_deal_created_event
from .portal_store import can_install_from_payload
from .portal_store import extract_event_deal_id
from .portal_store import extract_event_member_id
from .portal_store import safe_extract_event_member_id

logger = logging.getLogger(__name__)


def handle_bitrix_event(
    payload: dict[str, Any],
    *,
    database: Database,
    install_portal: Callable[[dict[str, Any]], dict[str, Any]],
    get_portal: Callable[[str], object],
    get_distribution_group: Callable[[str], dict[str, object] | None],
    get_bitrix_client: Callable[[str], BitrixListClient],
    record_diagnostic_log: Callable[..., None],
    now_factory: Callable[[], str],
    bitrix_event_deal_created: str,
    distribution_event_deal_created: str,
) -> dict[str, object]:
    event_name = str(payload.get("event") or "").strip().upper()
    logger.info("Received Bitrix event event=%s payload_keys=%s", event_name or "<empty>", sorted(payload.keys()))
    portal_member_id = as_optional_str(safe_extract_event_member_id(payload))
    record_diagnostic_log(
        source="bitrix_event",
        message="Received Bitrix event payload.",
        portal_member_id=portal_member_id,
        details={"event": event_name or None, "payload_keys": sorted(payload.keys())},
    )
    if event_name != bitrix_event_deal_created:
        record_diagnostic_log(
            source="bitrix_event",
            message="Ignored unsupported Bitrix event.",
            portal_member_id=portal_member_id,
            details={"event": event_name or None},
        )
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": event_name or None,
        }

    if can_install_from_payload(payload):
        install_portal(payload)

    portal_member_id = extract_event_member_id(payload)
    deal_id = extract_event_deal_id(payload)
    logger.info(
        "Processing ONCRMDEALADD portal=%s deal_id=%s",
        portal_member_id,
        deal_id,
    )
    record_diagnostic_log(
        source="bitrix_event",
        message="Processing ONCRMDEALADD.",
        portal_member_id=portal_member_id,
        deal_id=deal_id,
        details={"event": event_name},
    )
    return handle_deal_created_event(
        portal_member_id,
        deal_id,
        database=database,
        get_portal=get_portal,
        get_distribution_group=get_distribution_group,
        get_bitrix_client=get_bitrix_client,
        record_diagnostic_log=record_diagnostic_log,
        now_factory=now_factory,
        distribution_event_deal_created=distribution_event_deal_created,
    )
