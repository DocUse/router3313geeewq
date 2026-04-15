from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contracts import PortalAuth
from .database import Database


class PortalService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def install_portal(self, payload: dict[str, Any]) -> dict[str, Any]:
        auth = self._extract_auth_payload(payload)
        portal = PortalAuth(
            member_id=str(auth["member_id"]),
            domain=str(auth["domain"]),
            access_token=_as_optional_str(auth.get("access_token")),
            refresh_token=_as_optional_str(auth.get("refresh_token")),
            client_endpoint=_as_optional_str(auth.get("client_endpoint")),
            server_endpoint=_as_optional_str(auth.get("server_endpoint")),
            application_token=_as_optional_str(auth.get("application_token")),
            status=_as_optional_str(auth.get("status")),
        )
        self._upsert_portal(portal)
        return {
            "member_id": portal.member_id,
            "domain": portal.domain,
            "saved": True,
        }

    def get_portal(self, portal_member_id: str) -> PortalAuth:
        row = self.database.fetch_one("SELECT * FROM portals WHERE member_id = ?", (portal_member_id,))
        if row is None:
            raise ValueError(f"Portal {portal_member_id} is not installed")
        return PortalAuth(
            member_id=str(row["member_id"]),
            domain=str(row["domain"]),
            access_token=_as_optional_str(row["access_token"]),
            refresh_token=_as_optional_str(row["refresh_token"]),
            client_endpoint=_as_optional_str(row["client_endpoint"]),
            server_endpoint=_as_optional_str(row["server_endpoint"]),
            application_token=_as_optional_str(row["application_token"]),
            status=_as_optional_str(row["status"]),
        )

    def _extract_auth_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "member_id" in payload and "domain" in payload:
            return payload
        auth = payload.get("auth")
        if isinstance(auth, dict) and "member_id" in auth and "domain" in auth:
            return auth
        raise ValueError("Bitrix auth payload is missing member_id/domain")

    def _upsert_portal(self, portal: PortalAuth) -> None:
        now = _iso_now()
        existing = self.database.fetch_one("SELECT * FROM portals WHERE member_id = ?", (portal.member_id,))
        if existing:
            merged = PortalAuth(
                member_id=portal.member_id,
                domain=portal.domain or str(existing["domain"]),
                access_token=portal.access_token or _as_optional_str(existing["access_token"]),
                refresh_token=portal.refresh_token or _as_optional_str(existing["refresh_token"]),
                client_endpoint=portal.client_endpoint or _as_optional_str(existing["client_endpoint"]),
                server_endpoint=portal.server_endpoint or _as_optional_str(existing["server_endpoint"]),
                application_token=portal.application_token or _as_optional_str(existing["application_token"]),
                status=portal.status or _as_optional_str(existing["status"]),
            )
            self.database.execute(
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

        self.database.execute(
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


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _as_optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
