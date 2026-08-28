"""
ContextManager keeps per-session state so Larvi can resolve follow-up requests
like:

    User: Find my meeting with Ali tomorrow.
    Larvi: I found "Project Review" at 3 PM.
    User: Move it to 5 PM.       <-- "it" must resolve to the Project Review event

State kept per session:
- message history (role/content) for LLM context
- last_email: the most recently discussed email (id, subject, sender, snippet, body...)
- last_event: the most recently discussed calendar event (id, summary, start, end...)
- pending_confirmation: an action awaiting explicit user "yes" before execution
  (used for destructive / high-impact actions: send, delete, cancel, reschedule)

Backed by sqlite so state survives process restarts (simple, no external deps).
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Optional

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""


@contextmanager
def _conn():
    conn = sqlite3.connect(settings.STATE_DB_PATH)
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


DEFAULT_STATE = {
    "history": [],            # [{role, content}]
    "last_email": None,       # dict | None
    "last_event": None,       # dict | None
    "pending_confirmation": None,  # {"action": "...", "args": {...}, "agent": "email|calendar"}
}


class ContextManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state: dict[str, Any] = self._load()

    def _load(self) -> dict:
        with _conn() as c:
            row = c.execute(
                "SELECT data FROM sessions WHERE session_id = ?", (self.session_id,)
            ).fetchone()
        if row:
            loaded = json.loads(row[0])
            merged = {**DEFAULT_STATE, **loaded}
            return merged
        return json.loads(json.dumps(DEFAULT_STATE))  # deep copy

    def save(self):
        with _conn() as c:
            c.execute(
                "INSERT INTO sessions (session_id, data, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
                (self.session_id, json.dumps(self.state), time.time()),
            )

    # ---- history ----
    def add_message(self, role: str, content: str):
        self.state["history"].append({"role": role, "content": content})
        # Keep the last N turns to bound token usage
        self.state["history"] = self.state["history"][-30:]

    def get_history(self) -> list[dict]:
        return self.state["history"]

    # ---- last-referenced entities ----
    def set_last_email(self, email: dict):
        self.state["last_email"] = email

    def set_last_event(self, event: dict):
        self.state["last_event"] = event

    def get_last_email(self) -> Optional[dict]:
        return self.state.get("last_email")

    def get_last_event(self) -> Optional[dict]:
        return self.state.get("last_event")

    # ---- pending confirmations for destructive actions ----
    def set_pending_confirmation(self, agent: str, action: str, args: dict, human_summary: str):
        self.state["pending_confirmation"] = {
            "agent": agent,
            "action": action,
            "args": args,
            "human_summary": human_summary,
        }

    def pop_pending_confirmation(self) -> Optional[dict]:
        pending = self.state.get("pending_confirmation")
        self.state["pending_confirmation"] = None
        return pending

    def peek_pending_confirmation(self) -> Optional[dict]:
        return self.state.get("pending_confirmation")

    def context_snapshot(self) -> str:
        """Small text blurb injected into agent prompts so they can resolve 'it'/'that meeting'/etc."""
        parts = []
        if self.state.get("last_email"):
            e = self.state["last_email"]
            parts.append(f"Last referenced email: subject='{e.get('subject')}', from='{e.get('sender')}', id='{e.get('id')}'")
        if self.state.get("last_event"):
            ev = self.state["last_event"]
            parts.append(f"Last referenced calendar event: '{ev.get('summary')}' at {ev.get('start')}, id='{ev.get('id')}'")
        return "\n".join(parts) if parts else "No prior email/event referenced yet."
