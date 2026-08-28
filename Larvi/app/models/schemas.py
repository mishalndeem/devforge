from pydantic import BaseModel
from typing import Any, Optional


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_calls: list[dict[str, Any]] = []


class AuthStatusResponse(BaseModel):
    authenticated: bool
    mock_mode: bool
