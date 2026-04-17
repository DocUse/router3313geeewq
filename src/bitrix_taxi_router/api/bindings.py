from __future__ import annotations

import logging
from urllib.parse import urlsplit

from fastapi import Request

from ..service import PortalService
from ..settings import Settings

logger = logging.getLogger(__name__)


def ensure_binding_for_configured_portal(
    request: Request,
    *,
    service: PortalService,
    settings: Settings,
    portal_member_id: str | None,
    source: str,
) -> dict[str, object] | None:
    member_id = (portal_member_id or "").strip()
    if not member_id:
        return None

    event_handler_url = get_public_event_handler_url(request, settings=settings, route_name="bitrix_event_handler")
    if not event_handler_url:
        logger.warning("Skipping event binding source=%s portal=%s: public handler URL unavailable", source, member_id)
        record_app_diagnostic_log(
            service,
            source="event_binding",
            message="Skipped event binding because public handler URL is unavailable.",
            level="warning",
            portal_member_id=member_id,
            details={"trigger_source": source},
        )
        return None

    try:
        binding = service.ensure_configured_deal_created_event_binding(member_id, event_handler_url)
    except Exception:
        logger.exception(
            "Failed to ensure configured ONCRMDEALADD binding source=%s portal=%s handler=%s",
            source,
            member_id,
            event_handler_url,
        )
        record_app_diagnostic_log(
            service,
            source="event_binding",
            message="Failed to ensure ONCRMDEALADD binding.",
            level="error",
            portal_member_id=member_id,
            details={"trigger_source": source, "handler": event_handler_url},
        )
        raise

    logger.info(
        "Ensured configured ONCRMDEALADD binding source=%s portal=%s handler=%s result=%s",
        source,
        member_id,
        event_handler_url,
        binding,
    )
    record_app_diagnostic_log(
        service,
        source="event_binding",
        message="Ensured ONCRMDEALADD binding.",
        portal_member_id=member_id,
        details={"trigger_source": source, "handler": event_handler_url, "binding": binding},
    )
    return binding


def get_public_event_handler_url(request: Request, *, settings: Settings, route_name: str) -> str | None:
    configured_base_url = (settings.public_base_url or "").strip()
    if configured_base_url:
        normalized_base_url = configured_base_url.rstrip("/")
        parsed = urlsplit(normalized_base_url)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            logger.warning("APP_PUBLIC_BASE_URL is not usable for Bitrix event binding: %s", configured_base_url)
            return None
        return f"{normalized_base_url}{request.app.url_path_for(route_name)}"

    scheme = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").strip().lower()
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc or "").strip()
    if scheme != "https" or not host:
        return None

    hostname = urlsplit(f"{scheme}://{host}").hostname or ""
    if hostname in {"localhost", "127.0.0.1", "testserver"}:
        return None

    path = str(request.app.url_path_for(route_name))
    return f"{scheme}://{host}{path}"


def record_app_diagnostic_log(
    service: PortalService,
    *,
    source: str,
    message: str,
    level: str = "info",
    portal_member_id: str | None = None,
    deal_id: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    try:
        service.record_diagnostic_log(
            source=source,
            message=message,
            level=level,
            portal_member_id=portal_member_id,
            deal_id=deal_id,
            details=details,
        )
    except Exception:
        logger.exception("Failed to persist diagnostic log source=%s message=%s", source, message)
