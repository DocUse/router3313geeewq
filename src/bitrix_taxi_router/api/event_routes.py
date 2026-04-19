from __future__ import annotations

from datetime import datetime, timezone
import logging

from fastapi import FastAPI, HTTPException, Request

from .bindings import record_app_diagnostic_log
from .payloads import extract_deal_id_for_logging
from .payloads import extract_member_id_from_context
from .payloads import normalize_bitrix_payload
from .payloads import read_bitrix_payload
from ..bitrix_api import BitrixApiError
from ..service import PortalService

logger = logging.getLogger(__name__)


def register_event_routes(app: FastAPI, *, service: PortalService) -> None:
    @app.post("/api/bitrix/events", name="bitrix_event_handler")
    async def bitrix_event_handler(request: Request) -> dict[str, object]:
        payload = normalize_bitrix_payload(await read_bitrix_payload(request))
        portal_member_id = extract_member_id_from_context(payload)
        received_at = datetime.now(tz=timezone.utc)
        event_name = str(payload.get("event") or "").strip().upper() or None
        event_queue_ts = _parse_event_queue_timestamp(payload.get("ts"))
        delivery_delay_ms = None
        if event_queue_ts is not None:
            delivery_delay_ms = max(0, int((received_at - event_queue_ts).total_seconds() * 1000))
        logger.info(
            "Received /api/bitrix/events hit content_type=%s keys=%s",
            request.headers.get("content-type"),
            sorted(payload.keys()),
        )
        record_app_diagnostic_log(
            service,
            source="bitrix_event_endpoint",
            message="Received POST /api/bitrix/events hit.",
            portal_member_id=portal_member_id,
            deal_id=extract_deal_id_for_logging(payload),
            details={
                "content_type": request.headers.get("content-type"),
                "payload_keys": sorted(payload.keys()),
                "event": event_name,
                "received_at": received_at.isoformat(),
                "event_queue_ts": event_queue_ts.isoformat() if event_queue_ts is not None else None,
                "delivery_delay_ms": delivery_delay_ms,
            },
        )
        try:
            result = service.handle_bitrix_event(payload)
        except ValueError as exc:
            logger.exception("Bitrix event handler rejected payload")
            record_app_diagnostic_log(
                service,
                source="bitrix_event_endpoint",
                message="Rejected Bitrix event payload.",
                level="error",
                portal_member_id=portal_member_id,
                deal_id=extract_deal_id_for_logging(payload),
                details={"error": str(exc)},
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except BitrixApiError as exc:
            logger.exception("Bitrix event handler failed during Bitrix API call")
            record_app_diagnostic_log(
                service,
                source="bitrix_event_endpoint",
                message="Bitrix API call failed while processing event.",
                level="error",
                portal_member_id=portal_member_id,
                deal_id=extract_deal_id_for_logging(payload),
                details={"error": str(exc)},
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"status": "ok", "result": result}

    @app.get("/api/bitrix/events", name="bitrix_event_handler_probe")
    async def bitrix_event_handler_probe() -> dict[str, str]:
        record_app_diagnostic_log(
            service,
            source="bitrix_event_endpoint",
            message="Received GET /api/bitrix/events probe.",
        )
        return {"status": "ready"}

    @app.head("/api/bitrix/events")
    async def bitrix_event_handler_probe_head() -> dict[str, str]:
        return {}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}


def _parse_event_queue_timestamp(raw_value: object) -> datetime | None:
    if raw_value in (None, ""):
        return None
    try:
        timestamp = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
