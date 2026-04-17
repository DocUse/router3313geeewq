from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from .bindings import ensure_binding_for_configured_portal
from .bindings import record_app_diagnostic_log
from .payloads import extract_member_id_from_context
from .payloads import normalize_bitrix_payload
from .payloads import payload_contains_installable_auth
from .payloads import read_bitrix_payload
from ..service import PortalService
from ..settings import Settings
from ..ui import render_install_page


def register_install_routes(app: FastAPI, *, service: PortalService, settings: Settings) -> None:
    @app.get("/install", response_class=HTMLResponse)
    async def install_page_get(request: Request) -> str:
        member_id = (request.query_params.get("member_id") or "").strip() or None
        return render_install_page(initial_member_id=member_id)

    @app.head("/install")
    async def install_page_head() -> dict[str, str]:
        return {}

    @app.post("/install", response_class=HTMLResponse)
    async def install_page_post(request: Request) -> str:
        payload = normalize_bitrix_payload(await read_bitrix_payload(request))
        member_id = extract_member_id_from_context(payload)
        if payload_contains_installable_auth(payload):
            try:
                service.install_portal(payload)
                record_app_diagnostic_log(
                    service,
                    source="portal_context",
                    message="Saved portal context from /install.",
                    portal_member_id=member_id,
                )
                ensure_binding_for_configured_portal(
                    request,
                    service=service,
                    settings=settings,
                    portal_member_id=member_id,
                    source="install_page_post",
                )
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return render_install_page(initial_member_id=member_id)

    @app.get("/install/callback", response_class=HTMLResponse)
    async def install_callback_get() -> str:
        return "ready"

    @app.head("/install/callback")
    async def install_callback_head() -> dict[str, str]:
        return {}

    @app.post("/install/callback")
    async def install_callback(request: Request) -> dict[str, object]:
        payload = normalize_bitrix_payload(await read_bitrix_payload(request))
        try:
            saved = service.install_portal(payload)
            record_app_diagnostic_log(
                service,
                source="portal_context",
                message="Saved portal context from /install/callback.",
                portal_member_id=str(saved["member_id"]),
            )
            binding = ensure_binding_for_configured_portal(
                request,
                service=service,
                settings=settings,
                portal_member_id=str(saved["member_id"]),
                source="install_callback",
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", "portal": saved, "event_binding": binding}
