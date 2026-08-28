"""
Email tools — the actual functions the Email Agent calls.

Each function talks to the real Gmail API via googleapiclient. If MOCK_MODE is on
(or the user hasn't completed Google OAuth yet), a small in-memory mock mailbox is
used instead, so the whole agent pipeline can be demoed/tested without live
credentials. Swapping MOCK_MODE=false with valid OAuth tokens switches to real Gmail
with no code changes elsewhere in the system.

Every tool returns a plain dict: {"success": bool, ...data or "error": str}.
Larvi (the Master Agent) must never claim success unless success=True came back
from here.
"""
import base64
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings
from app.auth import google_auth

try:
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover
    build = None


# ---------------------------------------------------------------------------
# Mock mailbox — used when MOCK_MODE=true or before OAuth is completed.
# ---------------------------------------------------------------------------
_MOCK_INBOX = [
    {
        "id": "m1",
        "thread_id": "t1",
        "sender": "ahmed@example.com",
        "subject": "Project meeting tomorrow",
        "snippet": "Hi, let's meet tomorrow at 3 PM to review the project status...",
        "body": "Hi,\n\nLet's meet tomorrow at 3 PM to review the project status and next steps. "
                "Let me know if that works.\n\nThanks,\nAhmed",
        "date": (datetime.now() - timedelta(hours=3)).isoformat(),
        "unread": True,
    },
    {
        "id": "m2",
        "thread_id": "t2",
        "sender": "ali@example.com",
        "subject": "Re: Q3 budget",
        "snippet": "Thanks for sending this over, I'll review by EOD...",
        "body": "Thanks for sending this over, I'll review by EOD and get back to you.",
        "date": (datetime.now() - timedelta(days=1)).isoformat(),
        "unread": False,
    },
    {
        "id": "m3",
        "thread_id": "t3",
        "sender": "newsletter@service.com",
        "subject": "Your weekly digest",
        "snippet": "Here's what happened this week...",
        "body": "Here's what happened this week across your favorite topics.",
        "date": (datetime.now() - timedelta(days=2)).isoformat(),
        "unread": True,
    },
]


def _use_mock() -> bool:
    return settings.MOCK_MODE or not google_auth.is_authenticated()


def _gmail_service():
    creds = google_auth.load_credentials()
    return build("gmail", "v1", credentials=creds)


def _extract_body(payload: dict) -> str:
    """Best-effort plain-text body extraction from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "ignore")
    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    if "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "ignore")
    return ""


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

def get_recent_emails(max_results: int = 5, unread_only: bool = False) -> dict:
    """Fetch the most recent emails from the inbox."""
    try:
        if _use_mock():
            items = _MOCK_INBOX
            if unread_only:
                items = [m for m in items if m["unread"]]
            items = sorted(items, key=lambda m: m["date"], reverse=True)[:max_results]
            return {"success": True, "emails": items}

        service = _gmail_service()
        query = "is:unread" if unread_only else ""
        resp = service.users().messages().list(userId="me", maxResults=max_results, q=query).execute()
        msg_ids = resp.get("messages", [])
        emails = []
        for m in msg_ids:
            full = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in full["payload"].get("headers", [])}
            emails.append({
                "id": full["id"],
                "thread_id": full.get("threadId"),
                "sender": headers.get("from", "unknown"),
                "subject": headers.get("subject", "(no subject)"),
                "snippet": full.get("snippet", ""),
                "body": _extract_body(full["payload"]),
                "date": headers.get("date", ""),
                "unread": "UNREAD" in full.get("labelIds", []),
            })
        return {"success": True, "emails": emails}
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch recent emails: {e}"}


def search_emails(query: Optional[str] = None, sender: Optional[str] = None,
                   subject: Optional[str] = None, max_results: int = 5) -> dict:
    """Search emails by free-text keywords, sender, and/or subject."""
    try:
        if _use_mock():
            results = _MOCK_INBOX
            if sender:
                results = [m for m in results if sender.lower() in m["sender"].lower()]
            if subject:
                results = [m for m in results if subject.lower() in m["subject"].lower()]
            if query:
                q = query.lower()
                results = [m for m in results if q in m["subject"].lower() or q in m["body"].lower()]
            return {"success": True, "emails": results[:max_results]}

        service = _gmail_service()
        parts = []
        if query:
            parts.append(query)
        if sender:
            parts.append(f"from:{sender}")
        if subject:
            parts.append(f"subject:{subject}")
        gmail_query = " ".join(parts)
        resp = service.users().messages().list(userId="me", q=gmail_query, maxResults=max_results).execute()
        msg_ids = resp.get("messages", [])
        emails = []
        for m in msg_ids:
            full = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in full["payload"].get("headers", [])}
            emails.append({
                "id": full["id"],
                "thread_id": full.get("threadId"),
                "sender": headers.get("from", "unknown"),
                "subject": headers.get("subject", "(no subject)"),
                "snippet": full.get("snippet", ""),
                "body": _extract_body(full["payload"]),
                "date": headers.get("date", ""),
                "unread": "UNREAD" in full.get("labelIds", []),
            })
        return {"success": True, "emails": emails}
    except Exception as e:
        return {"success": False, "error": f"Failed to search emails: {e}"}


def read_email(email_id: str) -> dict:
    """Read the full content of a single email by id."""
    try:
        if _use_mock():
            match = next((m for m in _MOCK_INBOX if m["id"] == email_id), None)
            if not match:
                return {"success": False, "error": f"No email found with id '{email_id}'"}
            return {"success": True, "email": match}

        service = _gmail_service()
        full = service.users().messages().get(userId="me", id=email_id, format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in full["payload"].get("headers", [])}
        email = {
            "id": full["id"],
            "thread_id": full.get("threadId"),
            "sender": headers.get("from", "unknown"),
            "subject": headers.get("subject", "(no subject)"),
            "snippet": full.get("snippet", ""),
            "body": _extract_body(full["payload"]),
            "date": headers.get("date", ""),
        }
        return {"success": True, "email": email}
    except Exception as e:
        return {"success": False, "error": f"Failed to read email '{email_id}': {e}"}


def create_draft(to: str, subject: str, body: str) -> dict:
    """Create (but do not send) an email draft."""
    try:
        if not to or "@" not in to:
            return {"success": False, "error": f"'{to}' does not look like a valid recipient email address."}
        if _use_mock():
            return {"success": True, "draft_id": "draft_mock_1", "to": to, "subject": subject, "body": body}

        service = _gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return {"success": True, "draft_id": draft["id"], "to": to, "subject": subject, "body": body}
    except Exception as e:
        return {"success": False, "error": f"Failed to create draft: {e}"}


def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email immediately. Caller (Master Agent) is responsible for
    obtaining user confirmation before invoking this for important sends."""
    try:
        if not to or "@" not in to:
            return {"success": False, "error": f"'{to}' does not look like a valid recipient email address."}
        if _use_mock():
            return {"success": True, "message_id": "sent_mock_1", "to": to, "subject": subject}

        service = _gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"success": True, "message_id": sent["id"], "to": to, "subject": subject}
    except Exception as e:
        return {"success": False, "error": f"Failed to send email: {e}"}


def reply_email(email_id: str, body: str) -> dict:
    """Reply within an existing email thread."""
    try:
        if _use_mock():
            match = next((m for m in _MOCK_INBOX if m["id"] == email_id), None)
            if not match:
                return {"success": False, "error": f"No email found with id '{email_id}' to reply to."}
            return {"success": True, "message_id": f"reply_mock_{email_id}", "to": match["sender"],
                     "subject": f"Re: {match['subject']}", "body": body}

        service = _gmail_service()
        original = service.users().messages().get(userId="me", id=email_id, format="metadata",
                                                    metadataHeaders=["Subject", "From", "Message-ID"]).execute()
        headers = {h["name"].lower(): h["value"] for h in original["payload"].get("headers", [])}
        to_addr = headers.get("from")
        subject = headers.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        message = MIMEText(body)
        message["to"] = to_addr
        message["subject"] = subject
        message["In-Reply-To"] = headers.get("message-id", "")
        message["References"] = headers.get("message-id", "")
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(
            userId="me", body={"raw": raw, "threadId": original.get("threadId")}
        ).execute()
        return {"success": True, "message_id": sent["id"], "to": to_addr, "subject": subject}
    except Exception as e:
        return {"success": False, "error": f"Failed to reply to email '{email_id}': {e}"}


def summarize_email_text(body: str) -> str:
    """Lightweight local heuristic summary fallback (the Email Agent normally asks
    the LLM to summarize; this is used only if that path is unavailable)."""
    text = re.sub(r"\s+", " ", body).strip()
    return text[:280] + ("..." if len(text) > 280 else "")
