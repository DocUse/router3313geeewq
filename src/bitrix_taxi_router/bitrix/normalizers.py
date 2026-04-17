from __future__ import annotations

from typing import Any

from ..bitrix_api import BitrixApiError


def normalize_event_handlers(payload: dict[str, Any]) -> list[dict[str, object]]:
    result = payload.get("result")
    if not isinstance(result, list):
        raise BitrixApiError("Bitrix event handler payload has an unexpected format")

    handlers: list[dict[str, object]] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        event_name = str(item.get("event") or "").strip().upper()
        handler = str(item.get("handler") or "").strip()
        if not event_name or not handler:
            continue
        handlers.append({"event": event_name, "handler": handler})
    return handlers


def normalize_users(rows: list[dict[str, Any]]) -> list[dict[str, object]]:
    users: list[dict[str, object]] = []
    for row in rows:
        user_id = str(row.get("ID") or "").strip()
        if not user_id:
            continue

        full_name = " ".join(
            part for part in (str(row.get("NAME") or "").strip(), str(row.get("LAST_NAME") or "").strip()) if part
        )
        display_name = full_name or str(row.get("EMAIL") or "").strip() or f"Пользователь {user_id}"

        users.append(
            {
                "id": user_id,
                "name": display_name,
                "is_active": str(row.get("ACTIVE") or "").upper() != "N",
                "source": "bitrix:user.get",
            }
        )

    users.sort(key=lambda item: (str(item["name"]).casefold(), str(item["id"])))
    return users


def normalize_stages(rows: list[dict[str, Any]]) -> list[dict[str, object]]:
    stages: list[dict[str, object]] = []
    for row in rows:
        stage_id = str(row.get("STATUS_ID") or "").strip()
        name = str(row.get("NAME") or "").strip()
        if not stage_id or not name:
            continue

        raw_sort = row.get("SORT")
        try:
            sort_order = int(raw_sort) if raw_sort is not None else 999999
        except (TypeError, ValueError):
            sort_order = 999999

        stages.append(
            {
                "id": stage_id,
                "name": name,
                "sort": sort_order,
                "source": "bitrix:crm.status.list",
            }
        )

    stages.sort(key=lambda item: (int(item["sort"]), str(item["name"]).casefold(), str(item["id"])))
    return stages


def normalize_responsible_fields(payload: dict[str, Any]) -> list[dict[str, object]]:
    result = payload.get("result")
    fields_map: dict[str, Any] | None = None
    if isinstance(result, dict):
        nested_fields = result.get("fields")
        if isinstance(nested_fields, dict):
            fields_map = nested_fields
        else:
            fields_map = result
    if fields_map is None:
        raise BitrixApiError("Bitrix API field metadata response has an unexpected format")

    fields: list[dict[str, object]] = []
    for field_key, meta in fields_map.items():
        if not isinstance(meta, dict):
            continue

        field_id = str(meta.get("upperName") or field_key).strip()
        field_name = str(meta.get("title") or meta.get("formLabel") or meta.get("listLabel") or field_id).strip()
        normalized_type = str(meta.get("type") or meta.get("userType") or "").strip().lower()
        is_default = field_id == "ASSIGNED_BY_ID"
        is_read_only = bool(meta.get("isReadOnly"))
        is_multiple = bool(meta.get("isMultiple"))
        if normalized_type not in {"employee", "user"}:
            continue
        if is_read_only or is_multiple:
            continue

        fields.append(
            {
                "id": field_id,
                "name": field_name,
                "is_default": is_default,
                "source": "bitrix:crm.item.fields",
            }
        )

    fields.sort(key=lambda item: (not bool(item["is_default"]), str(item["name"]).casefold(), str(item["id"])))
    return fields
