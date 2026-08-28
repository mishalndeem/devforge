"""
Larvi FastAPI application.

Endpoints:
  POST /chat                    -> send a natural-language message to Larvi
  GET  /auth/google/login        -> start Gmail/Calendar OAuth
  GET  /auth/google/callback     -> OAuth redirect target
  GET  /auth/status              -> whether Google auth is completed / mock mode is on
  GET  /                         -> simple chat frontend
"""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.master_agent import handle_message
from app.auth import google_auth
from app.models.schemas import ChatRequest, ChatResponse, AuthStatusResponse

app = FastAPI(title="Larvi", description="Autonomous Email & Calendar AI Agent")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", response_class=HTMLResponse)
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse("<h1>Larvi is running</h1><p>POST to /chat to talk to it.</p>")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = handle_message(req.session_id, req.message)
        return ChatResponse(session_id=req.session_id, reply=result["reply"], tool_calls=result["tool_calls"])
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Larvi encountered an internal error: {e}"})


@app.get("/auth/status", response_model=AuthStatusResponse)
def auth_status():
    return AuthStatusResponse(authenticated=google_auth.is_authenticated(), mock_mode=settings.MOCK_MODE)


@app.get("/auth/google/login")
def google_login():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return JSONResponse(status_code=400, content={
            "error": "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not configured. "
                     "Set them in .env, or leave MOCK_MODE=true to demo without real Gmail/Calendar access."
        })
    return RedirectResponse(google_auth.build_auth_url())


@app.get("/auth/google/callback")
def google_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=400, content={"error": "Missing 'code' in callback request."})
    try:
        google_auth.exchange_code_for_token(code)
        return HTMLResponse("<h2>Google account connected. You can close this tab and return to Larvi.</h2>")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to complete Google auth: {e}"})


# Serve any static assets the frontend needs (kept simple: single index.html is enough)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
