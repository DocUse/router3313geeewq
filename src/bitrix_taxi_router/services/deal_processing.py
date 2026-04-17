from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Protocol

from ..bitrix_api import BitrixApiError
from ..database import Database
from .assignment import assign_deal_to_member
from .assignment import maybe_int
from .assignment import select_distribution_candidate
from .runtime_store import get_deal_runtime
from .runtime_store import get_member_last_assigned_map
from .runtime_store import record_and_return_deal_runtime
from .runtime_store import touch_member_runtime

logger = logging.getLogger(__name__)

DEAL_ENTITY_TYPE_ID = 2


class BitrixListClient(Protocol):
    def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, Any]:
        ...

    def call_list(self, method: str, params: dict[str, object] | None = None) -> list[dict[str, Any]]:
        ...


def handle_deal_created_event(
    portal_member_id: str,
    deal_id: str,
    *,
    database: Database,
    get_portal: Callable[[str], object],
    get_distribution_group: Callable[[str], dict[str, object] | None],
    get_bitrix_client: Callable[[str], BitrixListClient],
    record_diagnostic_log: Callable[..., None],
    now_factory: Callable[[], str],
    distribution_event_deal_created: str,
) -> dict[str, object]:
    get_portal(portal_member_id)

    existing_runtime = get_deal_runtime(
        database,
        portal_member_id,
        deal_id,
        distribution_event_deal_created,
    )
    if existing_runtime is not None:
        result = dict(existing_runtime)
        result["reason"] = "duplicate_event"
        logger.info(
            "Ignoring duplicate ONCRMDEALADD portal=%s deal_id=%s status=%s",
            portal_member_id,
            deal_id,
            existing_runtime.get("status"),
        )
        record_diagnostic_log(
            source="deal_assignment",
            message="Ignored duplicate ONCRMDEALADD event.",
            portal_member_id=portal_member_id,
            deal_id=deal_id,
            details={"status": str(existing_runtime.get("status") or "")},
        )
        return result

    config = get_distribution_group(portal_member_id)
    if config is None:
        logger.info("Ignoring deal assignment portal=%s deal_id=%s: no config", portal_member_id, deal_id)
        record_diagnostic_log(
            source="deal_assignment",
            message="Ignored deal because distribution group is not configured.",
            portal_member_id=portal_member_id,
            deal_id=deal_id,
        )
        return record_and_return_deal_runtime(
            database,
            portal_member_id,
            deal_id,
            event_type=distribution_event_deal_created,
            status="ignored",
            note="Distribution group is not configured",
            now_factory=now_factory,
        )
    if not bool(config.get("is_active")):
        logger.info("Ignoring deal assignment portal=%s deal_id=%s: config inactive", portal_member_id, deal_id)
        record_diagnostic_log(
            source="deal_assignment",
            message="Ignored deal because distribution group is inactive.",
            portal_member_id=portal_member_id,
            deal_id=deal_id,
        )
        return record_and_return_deal_runtime(
            database,
            portal_member_id,
            deal_id,
            event_type=distribution_event_deal_created,
            status="ignored",
            note="Distribution group is inactive",
            now_factory=now_factory,
        )
    if str(config.get("event_type") or "") != distribution_event_deal_created:
        logger.info(
            "Ignoring deal assignment portal=%s deal_id=%s: event_type=%s",
            portal_member_id,
            deal_id,
            config.get("event_type"),
        )
        record_diagnostic_log(
            source="deal_assignment",
            message="Ignored deal because distribution config does not handle deal creation.",
            portal_member_id=portal_member_id,
            deal_id=deal_id,
            details={"event_type": str(config.get("event_type") or "")},
        )
        return record_and_return_deal_runtime(
            database,
            portal_member_id,
            deal_id,
            event_type=distribution_event_deal_created,
            status="ignored",
            note="Distribution group does not handle deal creation events",
            now_factory=now_factory,
        )

    members = config.get("members")
    if not isinstance(members, list) or not members:
        logger.info("Ignoring deal assignment portal=%s deal_id=%s: no members", portal_member_id, deal_id)
        record_diagnostic_log(
            source="deal_assignment",
            message="Ignored deal because distribution group has no members.",
            portal_member_id=portal_member_id,
            deal_id=deal_id,
        )
        return record_and_return_deal_runtime(
            database,
            portal_member_id,
            deal_id,
            event_type=distribution_event_deal_created,
            status="ignored",
            note="Distribution group has no members",
            now_factory=now_factory,
        )

    client = get_bitrix_client(portal_member_id)
    deal = get_deal_item(client, deal_id)
    current_stage_id = extract_deal_stage_id(deal)
    if current_stage_id != str(config["distribution_stage_id"]):
        logger.info(
            "Ignoring deal assignment portal=%s deal_id=%s: stage=%s expected=%s",
            portal_member_id,
            deal_id,
            current_stage_id or "<empty>",
            config["distribution_stage_id"],
        )
        record_diagnostic_log(
            source="deal_assignment",
            message="Ignored deal because current stage does not match distribution stage.",
            portal_member_id=portal_member_id,
            deal_id=deal_id,
            details={
                "current_stage_id": current_stage_id or "",
                "expected_stage_id": str(config["distribution_stage_id"]),
            },
        )
        return record_and_return_deal_runtime(
            database,
            portal_member_id,
            deal_id,
            event_type=distribution_event_deal_created,
            status="ignored",
            note=f"Deal stage {current_stage_id or '<empty>'} does not match distribution stage",
            now_factory=now_factory,
        )

    selection = select_distribution_candidate(
        portal_member_id,
        client,
        config,
        last_assigned_map=get_member_last_assigned_map(database, portal_member_id),
    )
    if selection["selected_member"] is None:
        logger.info(
            "No available members for portal=%s deal_id=%s loads=%s",
            portal_member_id,
            deal_id,
            selection["loads"],
        )
        record_diagnostic_log(
            source="deal_assignment",
            message="No available distribution members: all limits are reached.",
            portal_member_id=portal_member_id,
            deal_id=deal_id,
            details={"loads": selection["loads"]},
        )
        return record_and_return_deal_runtime(
            database,
            portal_member_id,
            deal_id,
            event_type=distribution_event_deal_created,
            status="waiting",
            note="All distribution members reached their limits",
            extra={"loads": selection["loads"]},
            now_factory=now_factory,
        )

    selected_member = selection["selected_member"]
    selected_user_id = str(selected_member["user_id"])
    responsible_field_id = str(config["responsible_field_id"])

    assign_deal_to_member(client, deal_id, responsible_field_id, selected_user_id)
    touch_member_runtime(
        database,
        portal_member_id,
        selected_user_id,
        deal_id,
        now_factory=now_factory,
    )
    logger.info(
        "Assigned deal portal=%s deal_id=%s user_id=%s field=%s loads=%s",
        portal_member_id,
        deal_id,
        selected_user_id,
        responsible_field_id,
        selection["loads"],
    )
    record_diagnostic_log(
        source="deal_assignment",
        message="Assigned deal to distribution member.",
        portal_member_id=portal_member_id,
        deal_id=deal_id,
        details={
            "user_id": selected_user_id,
            "responsible_field_id": responsible_field_id,
            "loads": selection["loads"],
        },
    )
    return record_and_return_deal_runtime(
        database,
        portal_member_id,
        deal_id,
        event_type=distribution_event_deal_created,
        status="assigned",
        assigned_user_id=selected_user_id,
        assigned_field_id=responsible_field_id,
        note="Deal assigned after load calculation",
        extra={"loads": selection["loads"]},
        now_factory=now_factory,
    )


def get_deal_item(client: BitrixListClient, deal_id: str) -> dict[str, Any]:
    payload = client.call(
        "crm.item.get",
        {
            "entityTypeId": DEAL_ENTITY_TYPE_ID,
            "id": maybe_int(deal_id),
            "useOriginalUfNames": "Y",
        },
    )
    result = payload.get("result")
    if not isinstance(result, dict):
        raise BitrixApiError("Bitrix deal payload has an unexpected format")
    item = result.get("item")
    if not isinstance(item, dict):
        raise BitrixApiError("Bitrix deal payload is missing item data")
    return item


def extract_deal_stage_id(deal: dict[str, Any]) -> str:
    return str(deal.get("stageId") or deal.get("STAGE_ID") or "").strip()
