"""
Calendar Agent — owns everything calendar/scheduling-related. Decides which
Google Calendar tool(s) to call, executes them for real, and returns a
structured result plus a natural-language summary.
"""
from datetime import datetime

from app.tools import calendar_tools
from app.llm.gemini_client import run_tool_loop

TOOLS = [
    {
        "name": "get_events",
        "description": "List upcoming calendar events, optionally within a time window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "ISO-8601 start of window"},
                "time_max": {"type": "string", "description": "ISO-8601 end of window"},
                "max_results": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "search_events",
        "description": "Search calendar events by keyword in the title.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 10}},
            "required": ["query"],
        },
    },
    {
        "name": "check_availability",
        "description": "Check whether the user is free between two ISO-8601 timestamps.",
        "input_schema": {
            "type": "object",
            "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
            "required": ["start", "end"],
        },
    },
    {
        "name": "create_event",
        "description": "Create a new calendar event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start": {"type": "string", "description": "ISO-8601 datetime"},
                "end": {"type": "string", "description": "ISO-8601 datetime"},
                "attendees": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["summary", "start", "end"],
        },
    },
    {
        "name": "update_event",
        "description": "Update an existing event's title, time, or location (used for rescheduling).",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string"},
                "summary": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "location": {"type": "string"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "delete_event",
        "description": "Delete/cancel a calendar event by id.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
            "required": ["event_id"],
        },
    },
]

TOOL_IMPLS = {
    "get_events": calendar_tools.get_events,
    "search_events": calendar_tools.search_events,
    "check_availability": calendar_tools.check_availability,
    "create_event": calendar_tools.create_event,
    "update_event": calendar_tools.update_event,
    "delete_event": calendar_tools.delete_event,
}

SYSTEM_PROMPT = f"""You are the Calendar Agent inside Larvi, an autonomous email/calendar assistant.
You manage Google Calendar via the tools provided.

Today's date/time is: {datetime.now().isoformat()}

Rules:
- Resolve relative dates ("tomorrow", "next Monday", "in an hour") into concrete ISO-8601 datetimes
  yourself before calling a tool — tools do not understand relative dates.
- Always check availability before creating an event if there's any reasonable chance of conflict,
  unless the user/Master Agent has already confirmed they want it created regardless.
- Never claim an event was created/updated/deleted successfully unless the tool result has success=true.
- If a tool returns success=false, explain the error plainly.
- Finish with a short, clear natural-language summary including concrete values (event id, title,
  start/end time) so the Master Agent can use them or relay them to the user.
"""


def run_calendar_task(task: str, context_snapshot: str) -> dict:
    messages = [{
        "role": "user",
        "content": f"Context from earlier in the conversation:\n{context_snapshot}\n\nTask: {task}",
    }]
    result = run_tool_loop(SYSTEM_PROMPT, messages, TOOLS, TOOL_IMPLS)

    last_event = None
    for call in reversed(result["tool_calls"]):
        r = call["result"]
        if not isinstance(r, dict) or not r.get("success"):
            continue
        if "event" in r:
            last_event = r["event"]
            break
        if "events" in r and r["events"]:
            last_event = r["events"][0]
            break

    return {
        "final_text": result["final_text"],
        "tool_calls": result["tool_calls"],
        "last_event": last_event,
    }
