"""
Central configuration for Larvi.

Everything is loaded from environment variables (see .env.example). Never hard-code
API keys, client secrets, or tokens in source — this module only reads them.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root if present
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    GOOGLE_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
    ]

    TOKEN_STORE_PATH: str = os.getenv("TOKEN_STORE_PATH", "./data/token.json")
    STATE_DB_PATH: str = os.getenv("STATE_DB_PATH", "./data/larvi_state.db")

    # Demo / grading convenience: run without real Google credentials.
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() in ("1", "true", "yes")


settings = Settings()

# Ensure data dir exists
Path(settings.TOKEN_STORE_PATH).parent.mkdir(parents=True, exist_ok=True)
Path(settings.STATE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
