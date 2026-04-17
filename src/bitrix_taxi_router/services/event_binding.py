from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Protocol

from ..bitrix.normalizers import normalize_event_handlers

logger = logging.getLogger(__name__)


class BitrixCallClient(Protocol):
    def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, Any]:
        ...


def ensure_event_binding(
    portal_member_id: str,
    handler_url: str,
    *,
    event_name: str,
    ensure_message: str,
    already_exists_message: str,
    created_message: str,
    get_bitrix_client: Callable[[str], BitrixCallClient],
    record_diagnostic_log: Callable[..., None],
) -> dict[str, object]:
    normalized_handler_url = handler_url.strip()
    if not normalized_handler_url:
        raise ValueError("Event handler URL is required")

    logger.info(
        "Ensuring %s binding for portal=%s handler=%s",
        event_name,
        portal_member_id,
        normalized_handler_url,
    )
    record_diagnostic_log(
        source="event_binding",
        message=ensure_message,
        portal_member_id=portal_member_id,
        details={"handler": normalized_handler_url, "event": event_name},
    )
    client = get_bitrix_client(portal_member_id)
    existing = normalize_event_handlers(client.call("event.get"))
    for binding in existing:
        if binding["event"] != event_name:
            continue
        if normalize_handler_url(str(binding["handler"])) != normalize_handler_url(normalized_handler_url):
            continue
        logger.info(
            "%s binding already exists for portal=%s handler=%s",
            event_name,
            portal_member_id,
            normalized_handler_url,
        )
        record_diagnostic_log(
            source="event_binding",
            message=already_exists_message,
            portal_member_id=portal_member_id,
            details={"handler": normalized_handler_url, "event": event_name},
        )
        return {
            "event": event_name,
            "handler": normalized_handler_url,
            "already_bound": True,
            "bound": False,
        }

    client.call(
        "event.bind",
        {
            "event": event_name,
            "handler": normalized_handler_url,
        },
    )
    logger.info(
        "Created %s binding for portal=%s handler=%s",
        event_name,
        portal_member_id,
        normalized_handler_url,
    )
    record_diagnostic_log(
        source="event_binding",
        message=created_message,
        portal_member_id=portal_member_id,
        details={"handler": normalized_handler_url, "event": event_name},
    )
    return {
        "event": event_name,
        "handler": normalized_handler_url,
        "already_bound": False,
        "bound": True,
    }


def run_event_delivery_check(
    portal_member_id: str,
    handler_url: str,
    *,
    event_name: str,
    ensure_message: str,
    already_exists_message: str,
    created_message: str,
    get_bitrix_client: Callable[[str], BitrixCallClient],
    record_diagnostic_log: Callable[..., None],
) -> dict[str, object]:
    binding = ensure_event_binding(
        portal_member_id,
        handler_url,
        event_name=event_name,
        ensure_message=ensure_message,
        already_exists_message=already_exists_message,
        created_message=created_message,
        get_bitrix_client=get_bitrix_client,
        record_diagnostic_log=record_diagnostic_log,
    )
    check_id = f"delivery-check-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}"
    client = get_bitrix_client(portal_member_id)
    client.call(
        "event.test",
        {
            "check_id": check_id,
            "portal_member_id": portal_member_id,
            "handler_url": handler_url.strip(),
        },
    )
    record_diagnostic_log(
        source="event_delivery_check",
        message="Triggered Bitrix event delivery self-test.",
        portal_member_id=portal_member_id,
        details={"event": event_name, "check_id": check_id, "handler": handler_url.strip()},
    )
    return {
        "event": event_name,
        "check_id": check_id,
        "handler": handler_url.strip(),
        "binding": binding,
        "triggered": True,
    }


def ensure_configured_deal_created_event_binding(
    portal_member_id: str,
    handler_url: str,
    *,
    config: dict[str, object] | None,
    bitrix_event_deal_created: str,
    distribution_event_deal_created: str,
    ensure_deal_created_event_binding: Callable[[str, str], dict[str, object]],
    record_diagnostic_log: Callable[..., None],
) -> dict[str, object]:
    if config is None:
        logger.info("Skipping ONCRMDEALADD binding for portal=%s: no distribution config", portal_member_id)
        record_diagnostic_log(
            source="event_binding",
            message="Skipped ONCRMDEALADD binding because distribution group is not configured.",
            portal_member_id=portal_member_id,
        )
        return {
            "event": bitrix_event_deal_created,
            "handler": handler_url.strip(),
            "configured": False,
            "bound": False,
            "already_bound": False,
            "reason": "group_not_configured",
        }
    if str(config.get("event_type") or "") != distribution_event_deal_created:
        logger.info(
            "Skipping ONCRMDEALADD binding for portal=%s: unsupported config event_type=%s",
            portal_member_id,
            config.get("event_type"),
        )
        record_diagnostic_log(
            source="event_binding",
            message="Skipped ONCRMDEALADD binding because config event_type is unsupported.",
            portal_member_id=portal_member_id,
            details={"event_type": str(config.get("event_type") or "")},
        )
        return {
            "event": bitrix_event_deal_created,
            "handler": handler_url.strip(),
            "configured": True,
            "bound": False,
            "already_bound": False,
            "reason": "unsupported_event_type",
        }
    binding = ensure_deal_created_event_binding(portal_member_id, handler_url)
    binding["configured"] = True
    return binding


def normalize_handler_url(value: str) -> str:
    return value.strip().rstrip("/")
