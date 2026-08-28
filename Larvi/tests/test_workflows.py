"""
Tests for Larvi.

Two layers:
1. Tool-level tests (email_tools / calendar_tools in MOCK_MODE) — no network, no API
   keys required. These verify the underlying operations Larvi relies on.
2. Agent-level smoke tests (master_agent) — these DO call the Gemini API and
   require GEMINI_API_KEY to be set, so they're skipped automatically if it's absent.
   They exercise the three required multi-step workflows end to end.

Run with:  pytest tests/ -v
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

os.environ.setdefault("MOCK_MODE", "true")

from app.tools import email_tools, calendar_tools
from app.state.context_manager import ContextManager


# --------------------------------------------------------------------------
# 1. Tool-level tests (fast, no external calls)
# --------------------------------------------------------------------------

def test_get_recent_emails():
    result = email_tools.get_recent_emails(max_results=2)
    assert result["success"] is True
    assert len(result["emails"]) <= 2


def test_search_emails_by_sender():
    result = email_tools.search_emails(sender="ahmed")
    assert result["success"] is True
    assert any("ahmed" in e["sender"].lower() for e in result["emails"])


def test_search_emails_by_keyword_finds_meeting_email():
    result = email_tools.search_emails(query="meeting")
    assert result["success"] is True
    assert any("meeting" in e["subject"].lower() for e in result["emails"])


def test_read_email_not_found_returns_error():
    result = email_tools.read_email("does-not-exist")
    assert result["success"] is False
    assert "error" in result


def test_create_draft_invalid_recipient_rejected():
    result = email_tools.create_draft(to="not-an-email", subject="Hi", body="Hi")
    assert result["success"] is False


def test_send_email_success_mock():
    result = email_tools.send_email(to="test@example.com", subject="Hello", body="Hi there")
    assert result["success"] is True
    assert "message_id" in result


def test_calendar_get_events():
    result = calendar_tools.get_events()
    assert result["success"] is True
    assert isinstance(result["events"], list)


def test_calendar_create_and_update_event():
    created = calendar_tools.create_event(
        summary="Test Sync", start="2026-09-01T10:00:00", end="2026-09-01T10:30:00"
    )
    assert created["success"] is True
    event_id = created["event"]["id"]

    updated = calendar_tools.update_event(event_id, start="2026-09-01T15:00:00", end="2026-09-01T15:30:00")
    assert updated["success"] is True
    assert updated["event"]["start"] == "2026-09-01T15:00:00"


def test_calendar_delete_event():
    created = calendar_tools.create_event(summary="Temp", start="2026-09-02T10:00:00", end="2026-09-02T10:30:00")
    event_id = created["event"]["id"]
    deleted = calendar_tools.delete_event(event_id)
    assert deleted["success"] is True
    again = calendar_tools.delete_event(event_id)
    assert again["success"] is False  # already gone -> proper error, not a crash


def test_check_availability_detects_conflict():
    created = calendar_tools.create_event(summary="Busy Block", start="2026-09-03T09:00:00", end="2026-09-03T10:00:00")
    assert created["success"] is True
    avail = calendar_tools.check_availability("2026-09-03T09:30:00", "2026-09-03T09:45:00")
    assert avail["success"] is True
    assert avail["available"] is False


# --------------------------------------------------------------------------
# 2. Context manager tests
# --------------------------------------------------------------------------

def test_context_manager_persists_last_event_across_instances():
    session_id = f"test-{uuid.uuid4().hex[:8]}"
    ctx1 = ContextManager(session_id)
    ctx1.set_last_event({"id": "e1", "summary": "Project Review", "start": "2026-09-01T15:00:00"})
    ctx1.save()

    ctx2 = ContextManager(session_id)  # simulate a new request/turn
    last_event = ctx2.get_last_event()
    assert last_event is not None
    assert last_event["summary"] == "Project Review"


def test_pending_confirmation_roundtrip():
    session_id = f"test-{uuid.uuid4().hex[:8]}"
    ctx = ContextManager(session_id)
    ctx.set_pending_confirmation("calendar", "run_task", {"task": "cancel meeting"}, "Cancel Project Review at 3 PM?")
    ctx.save()

    ctx2 = ContextManager(session_id)
    pending = ctx2.peek_pending_confirmation()
    assert pending is not None
    assert pending["agent"] == "calendar"
    popped = ctx2.pop_pending_confirmation()
    assert popped is not None
    assert ctx2.peek_pending_confirmation() is None


# --------------------------------------------------------------------------
# 3. End-to-end multi-step workflow tests (require GEMINI_API_KEY)
# --------------------------------------------------------------------------
requires_llm = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set — skipping live-LLM workflow tests"
)


@requires_llm
def test_workflow_1_email_then_calendar():
    """Workflow 1: find an email and create a calendar event from it."""
    from app.master_agent import handle_message
    session_id = f"wf1-{uuid.uuid4().hex[:8]}"
    result = handle_message(
        session_id,
        "Find the email from Ahmed about the project meeting and add that meeting to my calendar.",
    )
    tool_names = [c["name"] for c in result["tool_calls"]]
    assert "email_agent" in tool_names
    assert "calendar_agent" in tool_names


@requires_llm
def test_workflow_2_context_followup_reschedule():
    """Workflow 2: ask about a meeting, then reference it with 'it' to reschedule (with confirmation)."""
    from app.master_agent import handle_message
    session_id = f"wf2-{uuid.uuid4().hex[:8]}"
    handle_message(session_id, "What meetings do I have tomorrow?")
    result = handle_message(session_id, "Move the Team Standup to 5 PM tomorrow.")
    # Should ask for confirmation (reschedule = important action) rather than execute immediately
    ctx = ContextManager(session_id)
    assert ctx.peek_pending_confirmation() is not None
    confirmed = handle_message(session_id, "yes, go ahead")
    assert "error" not in confirmed["reply"].lower()


@requires_llm
def test_workflow_3_conditional_email_to_calendar_with_availability_check():
    """Workflow 3: conditional multi-step — check email, extract time, check availability, create event."""
    from app.master_agent import handle_message
    session_id = f"wf3-{uuid.uuid4().hex[:8]}"
    result = handle_message(
        session_id,
        "Check whether I received an email from Ali about tomorrow's project meeting. "
        "If you find the meeting time, check whether I am free and add it to my calendar.",
    )
    tool_names = [c["name"] for c in result["tool_calls"]]
    assert "email_agent" in tool_names
