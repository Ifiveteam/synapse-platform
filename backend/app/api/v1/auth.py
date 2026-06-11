import json
import os
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

load_dotenv(override=True)

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback"
TOKEN_FILE = "google_tokens.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def save_tokens(tokens: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)


def load_tokens() -> dict | None:
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)


async def refresh_access_token() -> str | None:
    tokens = load_tokens()
    if not tokens or "refresh_token" not in tokens:
        return None

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": tokens["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        data = response.json()

    if "access_token" in data:
        tokens["access_token"] = data["access_token"]
        save_tokens(tokens)
        return data["access_token"]
    return None


@router.get("/login")
def login():
    """구글 OAuth 로그인 URL 반환"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(code: str):
    """구글 OAuth 콜백 - 토큰 받기"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        tokens = response.json()

    if "access_token" not in tokens:
        return {"error": "토큰 발급 실패", "detail": tokens}

    save_tokens(tokens)
    return RedirectResponse("http://localhost:3000?auth=success")


@router.get("/status")
def auth_status():
    """OAuth 연결 상태 확인"""
    tokens = load_tokens()
    if not tokens:
        return {"connected": False}
    return {"connected": True}
