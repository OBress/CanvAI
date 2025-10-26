"""FastAPI router for chat session and message endpoints."""

from typing import Dict

from fastapi import APIRouter, HTTPException

if __package__ in (None, ""):
    from chat_store import (  # type: ignore  # noqa: F401
        create_chat_message,
        create_chat_session,
        ensure_chat_storage,
        format_message,
        format_session,
        get_chat_session,
        list_chat_messages,
        list_chat_sessions,
    )
else:
    from .chat_store import (
        create_chat_message,
        create_chat_session,
        ensure_chat_storage,
        format_message,
        format_session,
        get_chat_session,
        list_chat_messages,
        list_chat_sessions,
    )

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions")
async def create_chat_session_endpoint(payload: Dict) -> Dict:
    """Create a new chat session and return its metadata."""
    ensure_chat_storage()
    user_id = (payload or {}).get("user_id")
    title = (payload or {}).get("title")
    if not user_id or not title:
        raise HTTPException(status_code=400, detail="user_id and title are required")
    session_row = create_chat_session(user_id, title)
    return {"session": format_session(session_row)}


@router.get("/sessions")
async def list_chat_sessions_endpoint() -> Dict:
    """List every stored chat session."""
    ensure_chat_storage()
    sessions = [format_session(row) for row in list_chat_sessions()]
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_chat_session_endpoint(session_id: int) -> Dict:
    """Return metadata for a single chat session."""
    ensure_chat_storage()
    session = get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"session": format_session(session)}


@router.post("/sessions/{session_id}/messages")
async def create_chat_message_endpoint(session_id: int, payload: Dict) -> Dict:
    """Create a message within the specified chat session."""
    ensure_chat_storage()
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    sender = (payload or {}).get("sender")
    message = (payload or {}).get("message")
    timestamp = (payload or {}).get("timestamp")
    if not sender or not message:
        raise HTTPException(status_code=400, detail="sender and message are required")
    try:
        message_row = create_chat_message(session_id, sender, message, timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": format_message(message_row)}


@router.get("/sessions/{session_id}/messages")
async def list_chat_messages_endpoint(session_id: int) -> Dict:
    """List all messages associated with a session."""
    ensure_chat_storage()
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    messages = [format_message(row) for row in list_chat_messages(session_id)]
    return {"messages": messages}


@router.get("/messages")
async def list_all_chat_messages_endpoint() -> Dict:
    """Return every message across all sessions."""
    ensure_chat_storage()
    messages = [format_message(row) for row in list_chat_messages()]
    return {"messages": messages}