from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request

from .bindings import ensure_binding_for_configured_portal
from .bindings import get_public_event_handler_url
from .bindings import record_app_diagnostic_log
from .payloads import normalize_bitrix_payload
from .payloads import read_bitrix_payload
from .responses import load_reference_data
from .responses import require_member_id
from ..service import PortalService
from ..settings import Settings


def register_ui_data_routes(app: FastAPI, *, service: PortalService, settings: Settings) -> None:
    @app.get("/api/ui/groups/reference-data")
    async def groups_reference_data(request: Request) -> dict[str, object]:
        member_id = require_member_id(request)
        return load_reference_data(service.get_reference_data, member_id)

    @app.get("/api/ui/groups/config")
    async def groups_config_get(request: Request) -> dict[str, object]:
        member_id = require_member_id(request)
        return {"config": load_reference_data(service.get_distribution_group, member_id)}

    @app.get("/api/ui/stats")
    async def stats_get(request: Request) -> dict[str, object]:
        member_id = require_member_id(request)
        return load_reference_data(service.get_distribution_statistics, member_id)

    @app.post("/api/ui/stats/event-delivery-check")
    async def stats_event_delivery_check(request: Request) -> dict[str, object]:
        member_id = require_member_id(request)
        event_handler_url = get_public_event_handler_url(
            request,
            settings=settings,
            route_name="bitrix_event_handler",
        )
        if not event_handler_url:
            record_app_diagnostic_log(
                service,
                source="event_delivery_check",
                message="Skipped self-test because public handler URL is unavailable.",
                level="warning",
                portal_member_id=member_id,
            )
            raise HTTPException(status_code=400, detail="Public event handler URL is unavailable")
        return load_reference_data(
            lambda portal_member_id: service.run_event_delivery_check(portal_member_id, event_handler_url),
            member_id,
        )

    @app.post("/api/ui/groups/config")
    async def groups_config_post(request: Request) -> dict[str, object]:
        member_id = require_member_id(request)
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON payload must be an object")
        saved = load_reference_data(lambda portal_member_id: service.save_distribution_group(portal_member_id, payload), member_id)
        record_app_diagnostic_log(
            service,
            source="distribution_config",
            message="Saved distribution group configuration.",
            portal_member_id=member_id,
            details={"event_type": payload.get("event_type"), "distribution_stage_id": payload.get("distribution_stage_id")},
        )
        binding = ensure_binding_for_configured_portal(
            request,
            service=service,
            settings=settings,
            portal_member_id=member_id,
            source="groups_config_post",
        )
        return {"status": "ok", "config": saved, "event_binding": binding}

    @app.post("/api/ui/groups/portal-context")
    async def groups_portal_context(request: Request) -> dict[str, object]:
        payload = normalize_bitrix_payload(await read_bitrix_payload(request))
        try:
            saved = service.install_portal(payload)
            record_app_diagnostic_log(
                service,
                source="portal_context",
                message="Saved portal context from /api/ui/groups/portal-context.",
                portal_member_id=str(saved["member_id"]),
            )
            binding = ensure_binding_for_configured_portal(
                request,
                service=service,
                settings=settings,
                portal_member_id=str(saved["member_id"]),
                source="groups_portal_context",
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", "portal": saved, "event_binding": binding}

    @app.get("/api/ui/groups/reference-data/users")
    async def groups_reference_users(request: Request) -> dict[str, object]:
        member_id = require_member_id(request)
        return {"items": load_reference_data(service.list_portal_users, member_id)}

    @app.get("/api/ui/groups/reference-data/stages")
    async def groups_reference_stages(request: Request) -> dict[str, object]:
        member_id = require_member_id(request)
        return {"items": load_reference_data(service.list_deal_stages, member_id)}

    @app.get("/api/ui/groups/reference-data/responsible-fields")
    async def groups_reference_responsible_fields(request: Request) -> dict[str, object]:
        member_id = require_member_id(request)
        return {"items": load_reference_data(service.list_responsible_fields, member_id)}
