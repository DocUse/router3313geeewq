from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request

from ..bitrix_api import BitrixApiError


def require_member_id(request: Request) -> str:
    member_id = (request.query_params.get("member_id") or "").strip()
    if not member_id:
        raise HTTPException(status_code=400, detail="member_id query parameter is required")
    return member_id


def load_reference_data(loader: Callable[[str], object], member_id: str) -> object:
    try:
        return loader(member_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BitrixApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
