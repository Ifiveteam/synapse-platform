import os
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback"

SCOPES = [
    "https://www.googleapis.com/auth/dataportability.myactivity.youtube",
]


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

    access_token = tokens.get("access_token")
    if not access_token:
        return {"error": "토큰 발급 실패", "detail": tokens}

    return {"access_token": access_token, "status": "success"}