"""FastAPI router exposing CRUD operations for user API keys."""

import sys
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

if __package__ in (None, ""):
    from user_store import (  # type: ignore  # noqa: F401
        ensure_user_storage,
        format_user_payload,
        get_user_settings,
        get_user_value,
        set_user_value,
    )
else:
    from .user_store import (  # type: ignore  # noqa: F401
        ensure_user_storage,
        format_user_payload,
        get_user_settings,
        get_user_value,
        set_user_value,
    )

router = APIRouter(prefix="/user", tags=["user"])

FieldPayload = Dict[str, str]


def _require_value(payload: Dict) -> str:
    value = (payload or {}).get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="value is required")
    if not isinstance(value, str):
        raise HTTPException(status_code=400, detail="value must be a string")
    return value


@router.on_event("startup")
def _startup() -> None:
    ensure_user_storage()


@router.get("/keys")
async def get_all_keys() -> Dict[str, Dict[str, str]]:
    """Return the full set of stored API keys."""
    ensure_user_storage()
    row = get_user_settings()
    return {"keys": format_user_payload(row)}


@router.get("/canvas_key")
async def get_canvas_key() -> FieldPayload:
    ensure_user_storage()
    return {"canvas_key": get_user_value("canvas_key")}


@router.post("/canvas_key")
async def set_canvas_key(payload: Dict) -> FieldPayload:
    ensure_user_storage()
    value = _require_value(payload)
    row = set_user_value("canvas_key", value)
    return {"canvas_key": row["canvas_key"]}


@router.get("/gemini_key")
async def get_gemini_key() -> FieldPayload:
    ensure_user_storage()
    return {"gemini_key": get_user_value("gemini_key")}


@router.post("/gemini_key")
async def set_gemini_key(payload: Dict) -> FieldPayload:
    ensure_user_storage()
    value = _require_value(payload)
    row = set_user_value("gemini_key", value)
    return {"gemini_key": row["gemini_key"]}


@router.get("/canvas_base_url")
async def get_canvas_base_url() -> FieldPayload:
    ensure_user_storage()
    return {"canvas_base_url": get_user_value("canvas_base_url")}


@router.post("/canvas_base_url")
async def set_canvas_base_url(payload: Dict) -> FieldPayload:
    ensure_user_storage()
    value = _require_value(payload)
    row = set_user_value("canvas_base_url", value)
    return {"canvas_base_url": row["canvas_base_url"]}


@router.get("/elevenlabs_api_key")
async def get_elevenlabs_api_key() -> FieldPayload:
    ensure_user_storage()
    return {"elevenlabs_api_key": get_user_value("elevenlabs_api_key")}


@router.post("/elevenlabs_api_key")
async def set_elevenlabs_api_key(payload: Dict) -> FieldPayload:
    ensure_user_storage()
    value = _require_value(payload)
    row = set_user_value("elevenlabs_api_key", value)
    return {"elevenlabs_api_key": row["elevenlabs_api_key"]}


@router.get("/openrouter_api_key")
async def get_openrouter_api_key() -> FieldPayload:
    ensure_user_storage()
    return {"openrouter_api_key": get_user_value("openrouter_api_key")}


@router.post("/openrouter_api_key")
async def set_openrouter_api_key(payload: Dict) -> FieldPayload:
    ensure_user_storage()
    value = _require_value(payload)
    row = set_user_value("openrouter_api_key", value)
    return {"openrouter_api_key": row["openrouter_api_key"]}
