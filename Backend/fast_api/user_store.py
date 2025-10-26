"""CSV-backed storage helpers for user API keys."""

from pathlib import Path
from threading import RLock
from typing import Dict, List
import csv

if __package__ in (None, ""):
    PROJECT_ROOT = Path(__file__).resolve().parents[1].parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

USER_DB_DIR = PROJECT_ROOT / "data" / "user_db"
USER_SETTINGS_FILE = USER_DB_DIR / "user_settings.csv"

USER_FIELDS = [
    "ID",
    "canvas_key",
    "gemini_key",
    "canvas_base_url",
    "elevenlabs_api_key",
    "openrouter_api_key",
]

_LOCK = RLock()


def _default_row() -> Dict[str, str]:
    """Return the default empty row for the user settings sheet."""
    return {
        "ID": "1",
        "canvas_key": "",
        "gemini_key": "",
        "canvas_base_url": "",
        "elevenlabs_api_key": "",
        "openrouter_api_key": "",
    }


def ensure_user_storage() -> None:
    """Create the user storage folder and starter CSV if missing."""
    USER_DB_DIR.mkdir(parents=True, exist_ok=True)
    if not USER_SETTINGS_FILE.exists():
        with USER_SETTINGS_FILE.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=USER_FIELDS)
            writer.writeheader()
            writer.writerow(_default_row())


def _read_rows() -> List[Dict[str, str]]:
    """Load all rows from the user settings CSV."""
    if not USER_SETTINGS_FILE.exists():
        return []
    with USER_SETTINGS_FILE.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp, fieldnames=USER_FIELDS)
        next(reader, None)
        return [row for row in reader]


def _write_rows(rows: List[Dict[str, str]]) -> None:
    """Persist rows back to disk, rewriting the CSV."""
    with USER_SETTINGS_FILE.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=USER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def get_user_settings() -> Dict[str, str]:
    """Return the singular user settings row, creating it if needed."""
    with _LOCK:
        ensure_user_storage()
        rows = _read_rows()
        if rows:
            return rows[0]
        default_row = _default_row()
        _write_rows([default_row])
        return default_row


def get_user_value(field: str) -> str:
    """Fetch an individual field from the user settings row."""
    if field not in USER_FIELDS:
        raise KeyError(f"Unknown user field '{field}'")
    if field == "ID":
        raise KeyError("Direct access to ID is not supported")
    row = get_user_settings()
    return row.get(field, "") or ""


def set_user_value(field: str, value: str) -> Dict[str, str]:
    """Update a single field in the user settings row and persist it."""
    if field not in USER_FIELDS:
        raise KeyError(f"Unknown user field '{field}'")
    if field == "ID":
        raise KeyError("Cannot mutate the ID field")

    with _LOCK:
        ensure_user_storage()
        rows = _read_rows()
        if rows:
            row = rows[0]
        else:
            row = _default_row()
            rows = [row]
        row[field] = value or ""
        _write_rows(rows)
        return row


def format_user_payload(row: Dict[str, str]) -> Dict[str, str]:
    """Drop internal fields and expose a clean payload for API responses."""
    return {
        "canvas_key": row.get("canvas_key", "") or "",
        "gemini_key": row.get("gemini_key", "") or "",
        "canvas_base_url": row.get("canvas_base_url", "") or "",
        "elevenlabs_api_key": row.get("elevenlabs_api_key", "") or "",
        "openrouter_api_key": row.get("openrouter_api_key", "") or "",
    }
