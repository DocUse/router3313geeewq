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
from ..ui import render_blank_page


def register_ui_page_routes(app: FastAPI, *, service: PortalService, settings: Settings) -> None:
    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return render_blank_page()

    @app.get("/ui/groups", response_class=HTMLResponse)
    async def groups_ui_get(request: Request) -> str:
        member_id = (request.query_params.get("member_id") or "").strip() or None
        return render_blank_page(initial_member_id=member_id)

    @app.head("/ui/groups")
    async def groups_ui_head() -> dict[str, str]:
        return {}

    @app.post("/ui/groups", response_class=HTMLResponse)
    async def groups_ui_post(request: Request) -> str:
        payload = normalize_bitrix_payload(await read_bitrix_payload(request))
        member_id = extract_member_id_from_context(payload)
        if payload_contains_installable_auth(payload):
            try:
                service.install_portal(payload)
                record_app_diagnostic_log(
                    service,
                    source="portal_context",
                    message="Saved portal context from /ui/groups.",
                    portal_member_id=member_id,
                )
                ensure_binding_for_configured_portal(
                    request,
                    service=service,
                    settings=settings,
                    portal_member_id=member_id,
                    source="groups_ui_post",
                )
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return render_blank_page(initial_member_id=member_id)
