from pydantic import BaseModel, Field
from typing import List


class ChatResponse(BaseModel):
    success: bool = True
    session_id: str
    message: str
    sources: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    type: str = "chat"