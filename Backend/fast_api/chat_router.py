"""FastAPI router for chat session and message endpoints."""

import sys
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

if __package__ in (None, ""):
    from chat_store import (  # type: ignore  # noqa: F401
        create_chat_message,
        create_chat_session,
        delete_chat_session,
        ensure_chat_storage,
        format_message,
        format_session,
        get_chat_session,
        list_chat_messages,
        list_chat_sessions,
        update_chat_session_title,
    )
else:
    from .chat_store import (
        create_chat_message,
        create_chat_session,
        delete_chat_session,
        ensure_chat_storage,
        format_message,
        format_session,
        get_chat_session,
        list_chat_messages,
        list_chat_sessions,
        update_chat_session_title,
    )

from vector_db.vector import perform_search  # type: ignore  # noqa: F401
from llm import (  # type: ignore  # noqa: F401
    generate_user_response_from_file,
    query_to_structured,
)

router = APIRouter(prefix="/chat", tags=["chat"])

def _latest_user_message(session_id: int) -> str:
    """Return the most recent user-authored message in a chat session."""
    messages = list_chat_messages(session_id)
    for row in reversed(messages):
        if row.get("sender") == "user":
            return row.get("message", "")
    return ""


def _get_last_n_messages(session_id: int, n: int = 10) -> List[Dict]:
    """Return the last N messages from a chat session for conversation context."""
    messages = list_chat_messages(session_id)
    # Return the last N messages (or all if fewer than N exist)
    return messages[-n:] if len(messages) > n else messages


def _collect_relevant_context(user_query: str, conversation_history: Optional[List[Dict]] = None) -> str:
    """Run the vector search + LLM summarization pipeline with conversation context."""
    try:
        structured = query_to_structured(user_query)
    except Exception as exc:  # defensive: LLM call may fail
        return f"I'm having trouble interpreting the question ({exc})."

    if not isinstance(structured, dict) or "error" in structured:
        detail = structured.get("error") if isinstance(structured, dict) else None
        return (
            "I couldn't understand that request just yet."
            if detail is None
            else f"I couldn't process the request: {detail}"
        )

    table = structured.get("table_to_query")
    if not table:
        return "Could you share a little more so I can look up the right information?"

    csv_filename = f"{table}.csv"
    try:
        search_results = perform_search(
            query=user_query,
            csv_filename=csv_filename,
            db_name=table,
        )
    except Exception as exc:
        return f"I ran into an issue searching the knowledge base ({exc})."

    if not search_results:
        return (
            "I couldn't find anything in your records that matches that just yet, "
            "but I'll keep looking as you share more."
        )

    combined_context = "\n\n".join(
        doc.page_content for doc, _score in search_results
    )

    try:
        response = generate_user_response_from_file(
            user_query=user_query,
            file_path=combined_context,
            conversation_history=conversation_history,
        )
    except Exception as exc:
        return f"I found some notes but couldn't craft a response ({exc})."

    return response or "Let me know how else I can help!"


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


@router.patch("/sessions/{session_id}")
async def update_chat_session_endpoint(session_id: int, payload: Dict) -> Dict:
    """Update chat session metadata (currently just the title)."""
    ensure_chat_storage()
    title = (payload or {}).get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    row = update_chat_session_title(session_id, title)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"session": format_session(row)}


@router.delete("/sessions/{session_id}")
async def delete_chat_session_endpoint(session_id: int) -> Dict:
    """Delete a chat session and associated messages."""
    ensure_chat_storage()
    deleted = delete_chat_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"ok": True}


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


@router.post("/sessions/{session_id}/assistant")
async def request_assistant_response_endpoint(session_id: int) -> Dict:
    """Generate an assistant response using the latest user input and store it."""
    ensure_chat_storage()
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    user_query = _latest_user_message(session_id)
    if not user_query:
        reply_text = "I'm ready whenever you are—what can I help you with today?"
    else:
        # Get the last 10 messages for conversation context
        conversation_history = _get_last_n_messages(session_id, n=10)
        reply_text = _collect_relevant_context(user_query, conversation_history)

    message_row = create_chat_message(session_id, "assistant", reply_text)
    return {"message": format_message(message_row)}


@router.get("/messages")
async def list_all_chat_messages_endpoint() -> Dict:
    """Return every message across all sessions."""
    ensure_chat_storage()
    messages = [format_message(row) for row in list_chat_messages()]
    return {"messages": messages}
