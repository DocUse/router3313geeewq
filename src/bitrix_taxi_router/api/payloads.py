from __future__ import annotations

import json
from urllib.parse import parse_qs

from fastapi import Request


async def read_bitrix_payload(request: Request) -> dict[str, object]:
    body = await request.body()
    if not body:
        return {}

    text = body.decode("utf-8", errors="replace").strip()
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type or text.startswith("{"):
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object")
        return payload

    return parse_form_encoded_payload(text)


def normalize_bitrix_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    if "auth" not in normalized and any(key in normalized for key in ("AUTH_ID", "REFRESH_ID", "DOMAIN")):
        protocol_raw = str(normalized.get("PROTOCOL") or "").strip().lower()
        scheme = "https" if protocol_raw in {"1", "https"} else "http"
        domain = str(normalized.get("DOMAIN") or "").strip()
        auth: dict[str, object] = {
            "member_id": normalized.get("member_id") or normalized.get("MEMBER_ID") or "",
            "domain": domain,
            "access_token": normalized.get("AUTH_ID") or "",
            "refresh_token": normalized.get("REFRESH_ID") or "",
            "client_endpoint": f"{scheme}://{domain}/rest/" if domain else "",
            "server_endpoint": "https://oauth.bitrix.info/rest/",
            "status": normalized.get("APP_STATUS") or normalized.get("status") or "",
        }
        normalized["auth"] = auth
    return normalized


def parse_form_encoded_payload(text: str) -> dict[str, object]:
    flat = parse_qs(text, keep_blank_values=True)
    nested: dict[str, object] = {}
    for raw_key, values in flat.items():
        value: object = values[-1] if values else ""
        tokens = raw_key.replace("]", "").split("[")
        cursor = nested
        for token in tokens[:-1]:
            existing = cursor.get(token)
            if not isinstance(existing, dict):
                existing = {}
                cursor[token] = existing
            cursor = existing
        cursor[tokens[-1]] = value
    return nested


def extract_member_id_from_context(payload: dict[str, object]) -> str | None:
    auth = payload.get("auth")
    if isinstance(auth, dict):
        member_id = str(auth.get("member_id") or "").strip()
        if member_id:
            return member_id
    member_id = str(payload.get("member_id") or payload.get("MEMBER_ID") or "").strip()
    return member_id or None


def payload_contains_installable_auth(payload: dict[str, object]) -> bool:
    auth = payload.get("auth")
    if not isinstance(auth, dict):
        return False
    return bool(str(auth.get("member_id") or "").strip() and str(auth.get("domain") or "").strip())


def extract_deal_id_for_logging(payload: dict[str, object]) -> str | None:
    data = payload.get("data")
    if isinstance(data, dict):
        fields = data.get("FIELDS")
        if isinstance(fields, dict):
            deal_id = str(fields.get("ID") or "").strip()
            if deal_id:
                return deal_id
    return None
