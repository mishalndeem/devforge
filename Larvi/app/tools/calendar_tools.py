"""
Calendar tools — the actual functions the Calendar Agent calls.

Same real-API / mock-mode pattern as email_tools.py. All times are handled as
ISO-8601 strings. Every tool returns {"success": bool, ...}.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.auth import google_auth

try:
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover
    build = None


# ---------------------------------------------------------------------------
# Mock calendar
# ---------------------------------------------------------------------------
_now = datetime.now().replace(minute=0, second=0, microsecond=0)
_MOCK_EVENTS = [
    {
        "id": "e1",
        "summary": "Team Standup",
        "start": (_now + timedelta(days=1, hours=9)).isoformat(),
        "end": (_now + timedelta(days=1, hours=9, minutes=30)).isoformat(),
        "attendees": ["team@example.com"],
        "location": "Zoom",
    },
    {
        "id": "e2",
        "summary": "Budget Review",
        "start": (_now + timedelta(days=2, hours=14)).isoformat(),
        "end": (_now + timedelta(days=2, hours=15)).isoformat(),
        "attendees": ["ali@example.com"],
        "location": "Conference Room B",
    },
]


def _use_mock() -> bool:
    return settings.MOCK_MODE or not google_auth.is_authenticated()

def _ensure_rfc3339(value: str) -> str:
    """
    Convert an ISO-8601 datetime into a Google Calendar-compatible
    RFC3339 datetime with an explicit timezone.
    """
    if not value:
        return value

    value = value.strip()

    # Already has UTC timezone
    if value.endswith("Z"):
        return value

    try:
        dt = datetime.fromisoformat(value)

        # If Gemini/tool gives a timezone-naive datetime,
        # treat it as UTC.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.isoformat()
    except ValueError:
        return value

def _calendar_service():
    creds = google_auth.load_credentials()
    return build("calendar", "v3", credentials=creds)


def get_events(time_min: Optional[str] = None, time_max: Optional[str] = None, max_results: int = 10) -> dict:
    """List upcoming events, optionally within a time window (ISO-8601 strings)."""
    try:
        if _use_mock():
            events = _MOCK_EVENTS
            if time_min:
                events = [e for e in events if e["start"] >= time_min]
            if time_max:
                events = [e for e in events if e["start"] <= time_max]
            return {"success": True, "events": events[:max_results]}

        service = _calendar_service()
        resp = service.events().list(
            calendarId="primary",
            timeMin=_ensure_rfc3339(
            time_min or datetime.now(timezone.utc).isoformat()
         ),
            timeMax=_ensure_rfc3339(time_max) if time_max else None,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for e in resp.get("items", []):
            events.append({
                "id": e["id"],
                "summary": e.get("summary", "(no title)"),
                "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
                "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
                "attendees": [a.get("email") for a in e.get("attendees", [])],
                "location": e.get("location", ""),
            })
        return {"success": True, "events": events}
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch events: {e}"}


def search_events(query: str, max_results: int = 10) -> dict:
    """Search calendar events by keyword in title/description."""
    try:
        if _use_mock():
            q = query.lower()
            matches = [e for e in _MOCK_EVENTS if q in e["summary"].lower()]
            return {"success": True, "events": matches[:max_results]}

        service = _calendar_service()
        resp = service.events().list(
            calendarId="primary", q=query, maxResults=max_results, singleEvents=True, orderBy="startTime"
        ).execute()
        events = []
        for e in resp.get("items", []):
            events.append({
                "id": e["id"],
                "summary": e.get("summary", "(no title)"),
                "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
                "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
                "attendees": [a.get("email") for a in e.get("attendees", [])],
                "location": e.get("location", ""),
            })
        return {"success": True, "events": events}
    except Exception as e:
        return {"success": False, "error": f"Failed to search events: {e}"}


def check_availability(start: str, end: str) -> dict:
    """Check whether the user is free between `start` and `end` (ISO-8601)."""
    try:
        if _use_mock():
            conflicts = [
                e for e in _MOCK_EVENTS
                if not (end <= e["start"] or start >= e["end"])
            ]
            return {"success": True, "available": len(conflicts) == 0, "conflicts": conflicts}

        service = _calendar_service()
        resp = service.freebusy().query(
            body={
              "timeMin": _ensure_rfc3339(start),
             "timeMax": _ensure_rfc3339(end),
             "items": [{"id": "primary"}],
                 }
        ).execute()
        busy = resp["calendars"]["primary"]["busy"]
        return {"success": True, "available": len(busy) == 0, "conflicts": busy}
    except Exception as e:
        return {"success": False, "error": f"Failed to check availability: {e}"}


def create_event(summary: str, start: str, end: str, attendees: Optional[list[str]] = None,
                  location: Optional[str] = None, description: Optional[str] = None) -> dict:
    """Create a new calendar event."""
    try:
        if not summary or not start or not end:
            return {"success": False, "error": "summary, start, and end are required to create an event."}
        if _use_mock():
            new_event = {
                "id": f"e_{uuid.uuid4().hex[:8]}",
                "summary": summary,
                "start": start,
                "end": end,
                "attendees": attendees or [],
                "location": location or "",
            }
            _MOCK_EVENTS.append(new_event)
            return {"success": True, "event": new_event}

        service = _calendar_service()
        body = {
         "summary": summary,
         "start": {"dateTime": _ensure_rfc3339(start)},
         "end": {"dateTime": _ensure_rfc3339(end)},
        }
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]
        if location:
            body["location"] = location
        if description:
            body["description"] = description
        created = service.events().insert(calendarId="primary", body=body).execute()
        return {"success": True, "event": {
            "id": created["id"], "summary": created.get("summary"),
            "start": created["start"].get("dateTime"), "end": created["end"].get("dateTime"),
        }}
    except Exception as e:
        return {"success": False, "error": f"Failed to create event: {e}"}


def update_event(event_id: str, summary: Optional[str] = None, start: Optional[str] = None,
                  end: Optional[str] = None, location: Optional[str] = None) -> dict:
    """Update fields of an existing event (e.g. reschedule = change start/end)."""
    try:
        if _use_mock():
            match = next((e for e in _MOCK_EVENTS if e["id"] == event_id), None)
            if not match:
                return {"success": False, "error": f"No event found with id '{event_id}'"}
            if summary:
                match["summary"] = summary
            if start:
                event["start"]["dateTime"] = _ensure_rfc3339(start)
            if end:
               event["end"]["dateTime"] = _ensure_rfc3339(end)
            if location:
                match["location"] = location
            return {"success": True, "event": match}

        service = _calendar_service()
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        if summary:
            event["summary"] = summary
        if start:
            event["start"]["dateTime"] = _ensure_rfc3339(start)
        if end:
            event["end"]["dateTime"] = _ensure_rfc3339(end)
        if location:
            event["location"] = location
        updated = service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
        return {"success": True, "event": {
            "id": updated["id"], "summary": updated.get("summary"),
            "start": updated["start"].get("dateTime"), "end": updated["end"].get("dateTime"),
        }}
    except Exception as e:
        return {"success": False, "error": f"Failed to update event '{event_id}': {e}"}


def delete_event(event_id: str) -> dict:
    """Delete/cancel an event. Master Agent must confirm with the user first."""
    try:
        if _use_mock():
            global _MOCK_EVENTS
            before = len(_MOCK_EVENTS)
            _MOCK_EVENTS = [e for e in _MOCK_EVENTS if e["id"] != event_id]
            if len(_MOCK_EVENTS) == before:
                return {"success": False, "error": f"No event found with id '{event_id}'"}
            return {"success": True, "deleted_id": event_id}

        service = _calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return {"success": True, "deleted_id": event_id}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete event '{event_id}': {e}"}
