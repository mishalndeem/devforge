"""
Larvi Master Agent — the central controller.

Flow: User -> Master Agent -> (Email Agent | Calendar Agent | both) -> tools/API -> Result -> User

Responsibilities implemented here:
- Understand the natural-language request (via Gemini + two "agent" tools)
- Select and call the right specialized agent(s), possibly in sequence, so multi-step
  workflows work (e.g. "find Ahmed's email about the meeting and add it to my calendar")
- Maintain conversation context across turns (ContextManager) so follow-ups like
  "move it to 5 PM" resolve correctly
- Require explicit user confirmation before destructive/important actions (send email,
  delete/cancel event, reschedule) unless the user has already confirmed in this message
- Never claim success unless the underlying tool reported success=true
- Handle failures gracefully with a clear message instead of crashing
"""
from datetime import datetime

from app.agents.email_agent import run_email_task
from app.agents.calendar_agent import run_calendar_task
from app.llm.gemini_client import run_tool_loop
from app.state.context_manager import ContextManager

CONFIRM_WORDS = {"yes", "yep", "yeah", "confirm", "go ahead", "do it", "sure", "proceed", "ok", "okay"}
CANCEL_WORDS = {"no", "nope", "cancel", "stop", "don't", "dont", "never mind", "nevermind"}


def _looks_like(text: str, words: set[str]) -> bool:
    t = text.strip().lower()
    return t in words or any(t.startswith(w) for w in words)


# ---------------------------------------------------------------------------
# Tools exposed to the Master Agent LLM: it can delegate to either sub-agent,
# call both in sequence for multi-step workflows, or pause for confirmation.
# ---------------------------------------------------------------------------
def _build_tools_and_impls(ctx: ContextManager):
    tools = [
        {
            "name": "email_agent",
            "description": (
                "Delegate an email-related task to the Email Agent (search, read, summarize, "
                "draft, send, reply). Give it a clear, self-contained natural-language instruction. "
                "It has access to the conversation context automatically."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"task": {"type": "string", "description": "The instruction to hand to the Email Agent"}},
                "required": ["task"],
            },
        },
        {
            "name": "calendar_agent",
            "description": (
                "Delegate a calendar/scheduling task to the Calendar Agent (view, search, check "
                "availability, create, update/reschedule, delete/cancel events). Give it a clear, "
                "self-contained natural-language instruction, including any concrete details (e.g. "
                "extracted meeting time/subject) discovered from a prior email_agent call."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"task": {"type": "string", "description": "The instruction to hand to the Calendar Agent"}},
                "required": ["task"],
            },
        },
        {
            "name": "request_confirmation",
            "description": (
                "Use this INSTEAD of email_agent/calendar_agent whenever the action is important/"
                "destructive: sending an email, deleting an email, cancelling a meeting, or "
                "rescheduling an existing meeting — UNLESS the user's current message already "
                "explicitly confirms they want it done. Calling this pauses execution and asks the "
                "user to confirm; do not call email_agent/calendar_agent for this action in the same turn."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "enum": ["email", "calendar"]},
                    "task": {"type": "string", "description": "The exact instruction to run once confirmed"},
                    "human_summary": {"type": "string", "description": "One sentence describing the action, to show the user"},
                },
                "required": ["agent", "task", "human_summary"],
            },
        },
    ]

    def _email_impl(task: str):
        result = run_email_task(task, ctx.context_snapshot())
        if result.get("last_email"):
            ctx.set_last_email(result["last_email"])
        return {"success": True, "summary": result["final_text"]}

    def _calendar_impl(task: str):
        result = run_calendar_task(task, ctx.context_snapshot())
        if result.get("last_event"):
            ctx.set_last_event(result["last_event"])
        return {"success": True, "summary": result["final_text"]}

    def _confirm_impl(agent: str, task: str, human_summary: str):
        ctx.set_pending_confirmation(agent, "run_task", {"task": task}, human_summary)
        return {"success": True, "note": "Confirmation requested; awaiting user response."}

    impls = {
        "email_agent": _email_impl,
        "calendar_agent": _calendar_impl,
        "request_confirmation": _confirm_impl,
    }
    return tools, impls


SYSTEM_PROMPT_TEMPLATE = """You are Larvi, an autonomous Email and Calendar AI agent. You never take real
actions yourself — you MUST delegate to the email_agent or calendar_agent tools for anything involving
actual email or calendar data. You may call both tools, and call a tool more than once, to complete
multi-step requests (e.g. find an email, extract details, then create a calendar event from it).

Today's date/time is: {now}

Known conversation context (use it to resolve "it", "that meeting", "that email", etc.):
{context}

Rules:
- Break multi-part requests into ordered agent calls. Use the result summary from one agent call as
  input to the next when needed (e.g. pass the extracted meeting time/subject from email_agent into
  calendar_agent's task).
- For important/destructive actions (sending an email, deleting an email, cancelling a meeting,
  rescheduling an existing meeting), call request_confirmation first instead of executing directly,
  UNLESS the user's current message already explicitly says to go ahead/confirms it.
- Never tell the user something succeeded unless the agent's summary confirms it succeeded. If an
  agent reports an error, explain it plainly and suggest what's needed to fix it (e.g. missing date,
  invalid recipient).
- Keep your final reply to the user concise, concrete, and helpful. Include key facts (times, names,
  subjects) rather than vague confirmations.
"""


def handle_message(session_id: str, user_text: str) -> dict:
    """Main entrypoint. Returns {"reply": str, "tool_calls": [...]} """
    ctx = ContextManager(session_id)

    # --- 1. Resolve any pending confirmation from the previous turn first ---
    pending = ctx.peek_pending_confirmation()
    if pending:
        if _looks_like(user_text, CONFIRM_WORDS):
            ctx.pop_pending_confirmation()
            agent = pending["agent"]
            task = pending["args"]["task"]
            try:
                if agent == "email":
                    result = run_email_task(f"{task} (user has explicitly confirmed — proceed now)", ctx.context_snapshot())
                    if result.get("last_email"):
                        ctx.set_last_email(result["last_email"])
                else:
                    result = run_calendar_task(f"{task} (user has explicitly confirmed — proceed now)", ctx.context_snapshot())
                    if result.get("last_event"):
                        ctx.set_last_event(result["last_event"])
                reply = result["final_text"]
            except Exception as e:
                reply = f"Something went wrong while completing that action: {e}"
            ctx.add_message("user", user_text)
            ctx.add_message("assistant", reply)
            ctx.save()
            return {"reply": reply, "tool_calls": []}

        if _looks_like(user_text, CANCEL_WORDS):
            ctx.pop_pending_confirmation()
            reply = "Okay, I won't do that. Let me know if you'd like something else."
            ctx.add_message("user", user_text)
            ctx.add_message("assistant", reply)
            ctx.save()
            return {"reply": reply, "tool_calls": []}
        # Ambiguous response to a pending confirmation — fall through to normal handling,
        # but keep the pending action alive in case they're just adding detail.

    # --- 2. Normal routing via the Master Agent LLM ---
    ctx.add_message("user", user_text)
    tools, impls = _build_tools_and_impls(ctx)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(now=datetime.now().isoformat(), context=ctx.context_snapshot())

    # Give the LLM the recent conversation as message history for continuity
    history_messages = [{"role": m["role"], "content": m["content"]} for m in ctx.get_history()]

    try:
        result = run_tool_loop(system_prompt, history_messages, tools, impls)
        reply = result["final_text"]
    except Exception as e:
        reply = f"Sorry — I hit an unexpected error handling that request: {e}"
        result = {"tool_calls": []}

    ctx.add_message("assistant", reply)
    ctx.save()
    return {"reply": reply, "tool_calls": result.get("tool_calls", [])}
