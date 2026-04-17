from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..contracts import PortalAuth
from ..database import Database
from .common import as_optional_str


def install_portal(
    database: Database,
    payload: dict[str, Any],
    *,
    now_factory: Callable[[], str],
) -> dict[str, Any]:
    auth = extract_auth_payload(payload)
    portal = PortalAuth(
        member_id=str(auth["member_id"]),
        domain=str(auth["domain"]),
        access_token=as_optional_str(auth.get("access_token")),
        refresh_token=as_optional_str(auth.get("refresh_token")),
        client_endpoint=as_optional_str(auth.get("client_endpoint")),
        server_endpoint=as_optional_str(auth.get("server_endpoint")),
        application_token=as_optional_str(auth.get("application_token")),
        status=as_optional_str(auth.get("status")),
    )
    upsert_portal(database, portal, now_factory=now_factory)
    return {
        "member_id": portal.member_id,
        "domain": portal.domain,
        "saved": True,
    }


def get_portal(database: Database, portal_member_id: str) -> PortalAuth:
    row = database.fetch_one("SELECT * FROM portals WHERE member_id = ?", (portal_member_id,))
    if row is None:
        raise ValueError(f"Portal {portal_member_id} is not installed")
    return PortalAuth(
        member_id=str(row["member_id"]),
        domain=str(row["domain"]),
        access_token=as_optional_str(row["access_token"]),
        refresh_token=as_optional_str(row["refresh_token"]),
        client_endpoint=as_optional_str(row["client_endpoint"]),
        server_endpoint=as_optional_str(row["server_endpoint"]),
        application_token=as_optional_str(row["application_token"]),
        status=as_optional_str(row["status"]),
    )


def upsert_portal(
    database: Database,
    portal: PortalAuth,
    *,
    now_factory: Callable[[], str],
) -> None:
    now = now_factory()
    existing = database.fetch_one("SELECT * FROM portals WHERE member_id = ?", (portal.member_id,))
    if existing:
        merged = PortalAuth(
            member_id=portal.member_id,
            domain=portal.domain or str(existing["domain"]),
            access_token=portal.access_token or as_optional_str(existing["access_token"]),
            refresh_token=portal.refresh_token or as_optional_str(existing["refresh_token"]),
            client_endpoint=portal.client_endpoint or as_optional_str(existing["client_endpoint"]),
            server_endpoint=portal.server_endpoint or as_optional_str(existing["server_endpoint"]),
            application_token=portal.application_token or as_optional_str(existing["application_token"]),
            status=portal.status or as_optional_str(existing["status"]),
        )
        database.execute(
            """
            UPDATE portals
            SET domain = ?, application_token = ?, access_token = ?, refresh_token = ?,
                client_endpoint = ?, server_endpoint = ?, status = ?, updated_at = ?
            WHERE member_id = ?
            """,
            (
                merged.domain,
                merged.application_token,
                merged.access_token,
                merged.refresh_token,
                merged.client_endpoint,
                merged.server_endpoint,
                merged.status,
                now,
                merged.member_id,
            ),
        )
        return

    database.execute(
        """
        INSERT INTO portals (
            member_id, domain, application_token, access_token, refresh_token,
            client_endpoint, server_endpoint, status, installed_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            portal.member_id,
            portal.domain,
            portal.application_token,
            portal.access_token,
            portal.refresh_token,
            portal.client_endpoint,
            portal.server_endpoint,
            portal.status,
            now,
            now,
        ),
    )


def extract_auth_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "member_id" in payload and "domain" in payload:
        return payload
    auth = payload.get("auth")
    if isinstance(auth, dict) and "member_id" in auth and "domain" in auth:
        return auth
    raise ValueError("Bitrix auth payload is missing member_id/domain")


def can_install_from_payload(payload: dict[str, Any]) -> bool:
    auth = payload.get("auth")
    if not isinstance(auth, dict):
        return False
    return bool(str(auth.get("member_id") or "").strip() and str(auth.get("domain") or "").strip())


def extract_event_member_id(payload: dict[str, Any]) -> str:
    auth = payload.get("auth")
    if isinstance(auth, dict):
        member_id = str(auth.get("member_id") or "").strip()
        if member_id:
            return member_id

    member_id = str(payload.get("member_id") or payload.get("MEMBER_ID") or "").strip()
    if member_id:
        return member_id
    raise ValueError("Bitrix event payload is missing member_id")


def extract_event_deal_id(payload: dict[str, Any]) -> str:
    data = payload.get("data")
    if isinstance(data, dict):
        fields = data.get("FIELDS")
        if isinstance(fields, dict):
            deal_id = str(fields.get("ID") or "").strip()
            if deal_id:
                return deal_id
    raise ValueError("Bitrix deal event payload is missing deal ID")


def safe_extract_event_member_id(payload: dict[str, Any]) -> str | None:
    auth = payload.get("auth")
    if isinstance(auth, dict):
        member_id = str(auth.get("member_id") or "").strip()
        if member_id:
            return member_id
    member_id = str(payload.get("member_id") or payload.get("MEMBER_ID") or "").strip()
    return member_id or None
