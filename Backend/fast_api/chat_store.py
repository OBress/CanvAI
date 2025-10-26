"""CSV-backed chat storage utilities."""

from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional
import csv

if __package__ in (None, ""):
    PROJECT_ROOT = Path(__file__).resolve().parents[1].parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHAT_DB_DIR = PROJECT_ROOT / "data" / "chat_db"
CHAT_SESSIONS_FILE = CHAT_DB_DIR / "chat_sessions.csv"
CHAT_MESSAGES_FILE = CHAT_DB_DIR / "chat_messages.csv"

SESSION_FIELDS = ["ID", "user_id", "title", "created_at"]
MESSAGE_FIELDS = ["ID", "session_id", "sender", "message", "timestamp"]

_LOCK = RLock()


def ensure_chat_storage() -> None:
    """Create the chat CSV directory and headers if they are missing."""
    CHAT_DB_DIR.mkdir(parents=True, exist_ok=True)
    if not CHAT_SESSIONS_FILE.exists():
        with CHAT_SESSIONS_FILE.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=SESSION_FIELDS)
            writer.writeheader()
    if not CHAT_MESSAGES_FILE.exists():
        with CHAT_MESSAGES_FILE.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=MESSAGE_FIELDS)
            writer.writeheader()


def _read_csv(path: Path, fieldnames: List[str]) -> List[Dict[str, str]]:
    """Load all rows from a CSV into memory as dictionaries."""
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp, fieldnames=fieldnames)
        next(reader, None)
        return [row for row in reader]


def _append_row(path: Path, fieldnames: List[str], row: Dict[str, str]) -> None:
    """Append a single row to the CSV file, preserving order of columns."""
    with path.open("a", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writerow(row)


def _next_identifier(rows: List[Dict[str, str]]) -> int:
    """Return the next integer ID by scanning existing rows."""
    max_id = 0
    for row in rows:
        try:
            value = int(row.get("ID", 0))
        except (TypeError, ValueError):
            continue
        max_id = max(max_id, value)
    return max_id + 1


def create_chat_session(user_id: str, title: str) -> Dict[str, str]:
    """Insert a new chat session record and return the stored row."""
    with _LOCK:
        ensure_chat_storage()
        sessions = _read_csv(CHAT_SESSIONS_FILE, SESSION_FIELDS)
        new_id = _next_identifier(sessions)
        created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        row = {
            "ID": str(new_id),
            "user_id": user_id,
            "title": title,
            "created_at": created_at,
        }
        _append_row(CHAT_SESSIONS_FILE, SESSION_FIELDS, row)
        return row


def list_chat_sessions() -> List[Dict[str, str]]:
    """Return every session row from the CSV store."""
    with _LOCK:
        ensure_chat_storage()
        return _read_csv(CHAT_SESSIONS_FILE, SESSION_FIELDS)


def get_chat_session(session_id: int) -> Optional[Dict[str, str]]:
    """Fetch a single session row by ID, or None if missing."""
    for session in list_chat_sessions():
        if session.get("ID") == str(session_id):
            return session
    return None


def create_chat_message(session_id: int, sender: str, message: str, timestamp: Optional[str] = None) -> Dict[str, str]:
    """Insert a message tied to a session and return the stored row."""
    with _LOCK:
        ensure_chat_storage()
        if get_chat_session(session_id) is None:
            raise ValueError(f"Session {session_id} does not exist.")
        messages = _read_csv(CHAT_MESSAGES_FILE, MESSAGE_FIELDS)
        new_id = _next_identifier(messages)
        ts = timestamp or datetime.utcnow().isoformat(timespec="seconds") + "Z"
        row = {
            "ID": str(new_id),
            "session_id": str(session_id),
            "sender": sender,
            "message": message,
            "timestamp": ts,
        }
        _append_row(CHAT_MESSAGES_FILE, MESSAGE_FIELDS, row)
        return row


def list_chat_messages(session_id: Optional[int] = None) -> List[Dict[str, str]]:
    """Return all messages, optionally filtered to one session."""
    with _LOCK:
        ensure_chat_storage()
        messages = _read_csv(CHAT_MESSAGES_FILE, MESSAGE_FIELDS)
        if session_id is None:
            return messages
        sid = str(session_id)
        return [row for row in messages if row.get("session_id") == sid]


def format_session(row: Dict[str, str]) -> Dict[str, str]:
    """Convert raw CSV session row to API response schema."""
    return {
        "id": int(row["ID"]),
        "user_id": row["user_id"],
        "title": row["title"],
        "created_at": row["created_at"],
    }


def format_message(row: Dict[str, str]) -> Dict[str, str]:
    """Convert raw CSV message row to API response schema."""
    return {
        "id": int(row["ID"]),
        "session_id": int(row["session_id"]),
        "sender": row["sender"],
        "message": row["message"],
        "timestamp": row["timestamp"],
    }
