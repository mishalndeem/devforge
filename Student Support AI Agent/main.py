from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import run_agent

app = FastAPI(
    title="DEVFORGE Student Support AI Agent",
    description="An AI agent built with LangChain, LangGraph, FastAPI and Ollama Cloud.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {
        "message": "Welcome to DEVFORGE Student Support AI Agent",
        "documentation": "/docs",
        "chat_ui": "/ui",
    }


@app.get("/ui")
def chat_ui():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "DEVFORGE Student Support AI Agent",
    }


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:
        result = run_agent(request.message)

        return {
            "reply": result["reply"],
            "category": result["category"],
            "agent": "DEVFORGE Student Support AI Agent",
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(error)}",
        )
