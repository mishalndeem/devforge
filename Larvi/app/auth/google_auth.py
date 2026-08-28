"""
Handles Google OAuth 2.0 for Gmail + Calendar access.

Flow:
1. GET /auth/google/login  -> redirects the user to Google's consent screen
2. Google redirects back to GOOGLE_REDIRECT_URI with an auth code
3. GET /auth/google/callback exchanges the code for access + refresh tokens
4. Tokens are cached at settings.TOKEN_STORE_PATH and auto-refreshed on use

No credentials are ever hard-coded — GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET come
from the environment (see .env.example).
"""
import json
import os
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

from app.config import settings


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def build_auth_url() -> str:
    flow = Flow.from_client_config(
        _client_config(), scopes=settings.GOOGLE_SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    auth_url, _state = flow.authorization_url(
        access_type="offline",       # request a refresh token
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code_for_token(code: str) -> Credentials:
    flow = Flow.from_client_config(
        _client_config(), scopes=settings.GOOGLE_SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    _save_credentials(creds)
    return creds


def _save_credentials(creds: Credentials):
    Path(settings.TOKEN_STORE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(settings.TOKEN_STORE_PATH, "w") as f:
        f.write(creds.to_json())


def load_credentials() -> Optional[Credentials]:
    """Load cached credentials, refreshing the access token if it has expired."""
    if not os.path.exists(settings.TOKEN_STORE_PATH):
        return None
    with open(settings.TOKEN_STORE_PATH) as f:
        data = json.load(f)
    creds = Credentials.from_authorized_user_info(data, settings.GOOGLE_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)
    return creds


def is_authenticated() -> bool:
    creds = load_credentials()
    return bool(creds and creds.valid)
