from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortalAuth:
    member_id: str
    domain: str
    access_token: str | None
    refresh_token: str | None
    client_endpoint: str | None
    server_endpoint: str | None
    application_token: str | None
    status: str | None
