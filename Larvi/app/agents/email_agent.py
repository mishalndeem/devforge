"""
Email Agent — owns everything email-related. Given a natural-language task
(passed down from the Master Agent, with relevant context), it decides which
Gmail tool(s) to call, in what order, executes them for real, and returns a
structured result plus a natural-language summary.
"""
from app.tools import email_tools
from app.llm.gemini_client import run_tool_loop

TOOLS = [
    {
        "name": "get_recent_emails",
        "description": "Fetch the most recent emails from the inbox, optionally unread only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "How many emails to return", "default": 5},
                "unread_only": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "search_emails",
        "description": "Search emails by free-text keywords, sender address/name, and/or subject text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text keywords to search for"},
                "sender": {"type": "string", "description": "Sender name or email address"},
                "subject": {"type": "string", "description": "Text expected in the subject line"},
                "max_results": {"type": "integer", "default": 5},
            },
        },
    },
    {
        "name": "read_email",
        "description": "Read the full body of a specific email by its id.",
        "input_schema": {
            "type": "object",
            "properties": {"email_id": {"type": "string"}},
            "required": ["email_id"],
        },
    },
    {
        "name": "create_draft",
        "description": "Create an email draft without sending it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "send_email",
        "description": "Send a brand-new email immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "reply_email",
        "description": "Reply within an existing email thread by email id.",
        "input_schema": {
            "type": "object",
            "properties": {"email_id": {"type": "string"}, "body": {"type": "string"}},
            "required": ["email_id", "body"],
        },
    },
]

TOOL_IMPLS = {
    "get_recent_emails": email_tools.get_recent_emails,
    "search_emails": email_tools.search_emails,
    "read_email": email_tools.read_email,
    "create_draft": email_tools.create_draft,
    "send_email": email_tools.send_email,
    "reply_email": email_tools.reply_email,
}

SYSTEM_PROMPT = """You are the Email Agent inside Larvi, an autonomous email/calendar assistant.
You manage Gmail via the tools provided: searching, reading, summarizing, drafting, sending, and replying.

Rules:
- Always use a tool to look up real data before claiming anything about the user's inbox.
- Never claim an email was sent/drafted successfully unless the tool result has success=true.
- If a tool returns success=false, explain the error plainly and suggest what info is missing.
- When summarizing emails, be concise and pull out the concrete facts (dates, times, names, asks).
- When the task involves sending or an important action, still call the tool if the Master Agent
  has already told you the user confirmed — you don't ask for confirmation yourself, the Master Agent does.
- Finish with a short, clear natural-language summary of what you found or did, including concrete
  values (e.g. exact email id, subject, sender, extracted meeting time) so the Master Agent can use them.
"""


def run_email_task(task: str, context_snapshot: str) -> dict:
    """
    Executes an email-related task end to end (may involve multiple tool calls),
    and returns {final_text, tool_calls, structured} for the Master Agent to consume.
    """
    messages = [{
        "role": "user",
        "content": f"Context from earlier in the conversation:\n{context_snapshot}\n\nTask: {task}",
    }]
    result = run_tool_loop(SYSTEM_PROMPT, messages, TOOLS, TOOL_IMPLS)

    # Surface the most recently touched email so the Master Agent can update context
    last_email = None
    for call in reversed(result["tool_calls"]):
        r = call["result"]
        if not isinstance(r, dict) or not r.get("success"):
            continue
        if "email" in r:
            last_email = r["email"]
            break
        if "emails" in r and r["emails"]:
            last_email = r["emails"][0]
            break

    return {
        "final_text": result["final_text"],
        "tool_calls": result["tool_calls"],
        "last_email": last_email,
    }
