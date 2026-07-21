from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import uuid   # <-- ADD THIS

from app.rag.retriever import retrieve
from app.rag.prompt_builder import build_prompt
from app.services.llm_service import generate_response

from app.schemas.chat import ChatResponse
from app.utils.suggestions import get_suggestions

# <-- ADD THIS
from app.services.memory_service import (
    get_history,
    add_message
)

from app.services.safety_service import (
    safety_check,
    get_safe_response
)

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


@router.post("/chat")
def chat(request: ChatRequest):

    # Step 7.4
    session_id = request.session_id

    if not session_id:
        session_id = str(uuid.uuid4())

    # Step 8.4 - Safety Check
    check = safety_check(request.message)

    if not check["allowed"]:
        return ChatResponse(
            session_id=session_id,
            message=get_safe_response(check["type"]),
            sources=[],
            suggestions=get_suggestions()
        )

    # Only continue if the message is safe
    chunks = retrieve(request.message)
    
    if not chunks:

        return ChatResponse(
            session_id=session_id,
            message=(
             "I couldn't find verified information "
             "about that in the clinic knowledge base."
            ),
            sources=[],
            suggestions=get_suggestions()
        )

    # Step 7.5
    history = get_history(session_id)

    prompt, sources = build_prompt(
        request.message,
        chunks,
        history
    )

    answer = generate_response(prompt)

    # Save conversation
    add_message(
        session_id,
        "user",
        request.message
    )

    add_message(
        session_id,
        "assistant",
        answer
    )

    return ChatResponse(
    session_id=session_id,
    message=answer,
    sources=sources,
    suggestions=get_suggestions()
)