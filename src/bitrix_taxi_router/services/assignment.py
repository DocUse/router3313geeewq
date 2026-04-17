from __future__ import annotations

from typing import Protocol

from .common import coerce_int
from .common import maybe_int


DEAL_ENTITY_TYPE_ID = 2


class BitrixListClient(Protocol):
    def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, Any]:
        ...

    def call_list(self, method: str, params: dict[str, object] | None = None) -> list[dict[str, Any]]:
        ...


def select_distribution_candidate(
    portal_member_id: str,
    client: BitrixListClient,
    config: dict[str, object],
    *,
    last_assigned_map: dict[str, str | None],
) -> dict[str, object]:
    members = config.get("members")
    if not isinstance(members, list):
        raise ValueError("Stored distribution members payload must be a list")

    responsible_field_id = str(config["responsible_field_id"])
    load_stage_ids = config.get("load_stage_ids")
    if not isinstance(load_stage_ids, list):
        raise ValueError("Stored distribution load stages payload must be a list")

    loads: list[dict[str, object]] = []
    available_members: list[dict[str, object]] = []
    for raw_member in members:
        if not isinstance(raw_member, dict):
            continue
        user_id = str(raw_member.get("user_id") or "").strip()
        if not user_id:
            continue
        limit_value = coerce_int(raw_member.get("limit"), field_name=f"Member limit for {user_id}")
        sort_order = coerce_int(raw_member.get("sort_order"), field_name=f"Member sort order for {user_id}")
        current_load = count_member_load(client, responsible_field_id, load_stage_ids, user_id)
        last_assigned_at = last_assigned_map.get(user_id)
        descriptor = {
            "user_id": user_id,
            "limit": limit_value,
            "sort_order": sort_order,
            "current_load": current_load,
            "last_assigned_at": last_assigned_at,
        }
        loads.append(descriptor)
        if current_load < limit_value:
            available_members.append(descriptor)

    available_members.sort(
        key=lambda member: (
            int(member["current_load"]),
            str(member.get("last_assigned_at") or ""),
            int(member["sort_order"]),
        )
    )
    selected_member = available_members[0] if available_members else None
    return {"selected_member": selected_member, "loads": loads}


def count_member_load(
    client: BitrixListClient,
    responsible_field_id: str,
    load_stage_ids: list[object],
    user_id: str,
) -> int:
    filter_field = resolve_responsible_field_api_name(responsible_field_id)
    items = client.call_list(
        "crm.item.list",
        {
            "entityTypeId": DEAL_ENTITY_TYPE_ID,
            "select": ["id"],
            "filter": {
                "@stageId": [str(stage_id) for stage_id in load_stage_ids],
                f"@{filter_field}": [maybe_int(user_id)],
            },
            "useOriginalUfNames": "Y",
        },
    )
    return len(items)


def assign_deal_to_member(
    client: BitrixListClient,
    deal_id: str,
    responsible_field_id: str,
    user_id: str,
) -> None:
    field_name = resolve_responsible_field_api_name(responsible_field_id)
    client.call(
        "crm.item.update",
        {
            "entityTypeId": DEAL_ENTITY_TYPE_ID,
            "id": maybe_int(deal_id),
            "fields": {field_name: maybe_int(user_id)},
            "useOriginalUfNames": "Y",
        },
    )
def resolve_responsible_field_api_name(field_id: str) -> str:
    normalized = field_id.strip().upper()
    if normalized == "ASSIGNED_BY_ID":
        return "assignedById"
    return field_id.strip()
