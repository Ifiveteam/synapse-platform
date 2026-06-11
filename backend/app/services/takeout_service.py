import base64
import os
import re
import tempfile

import httpx

from app.api.v1.auth import load_tokens, refresh_access_token


async def get_access_token() -> str | None:
    tokens = load_tokens()
    if not tokens:
        return None
    return tokens.get("access_token")


async def _get(client: httpx.AsyncClient, url: str, token: str, **kwargs) -> httpx.Response:
    response = await client.get(url, headers={"Authorization": f"Bearer {token}"}, **kwargs)
    if response.status_code == 401:
        token = await refresh_access_token()
        if not token:
            return response
        response = await client.get(url, headers={"Authorization": f"Bearer {token}"}, **kwargs)
    return response


async def find_takeout_email() -> dict | None:
    """Gmail에서 테이크아웃 준비 완료 메일 찾기"""
    token = await get_access_token()
    if not token:
        return None

    async with httpx.AsyncClient() as client:
        response = await _get(
            client,
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            token,
            params={
                "q": "from:noreply@google.com newer_than:30d",
                "maxResults": 10,
            },
        )
        messages = response.json().get("messages", [])
        if not messages:
            return None
        return messages[0]


async def get_download_links_from_email(message_id: str) -> list[str]:
    """메일 본문에서 Takeout 아카이브 URL 추출 후 실제 다운로드 링크 획득"""
    token = await get_access_token()
    if not token:
        return []

    async with httpx.AsyncClient() as client:
        response = await _get(
            client,
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            token,
            params={"format": "full"},
        )
        data = response.json()

    # 메일 본문 디코딩
    body = ""
    payload = data.get("payload", {})
    parts = payload.get("parts", [payload])
    for part in parts:
        if part.get("mimeType") in ("text/html", "text/plain"):
            encoded = part.get("body", {}).get("data", "")
            if encoded:
                body += base64.urlsafe_b64decode(encoded + "==").decode("utf-8", errors="ignore")

    # Takeout 관리 페이지 URL에서 아카이브 ID 추출
    archive_ids = re.findall(r'takeout\.google\.com/manage/archive/([a-f0-9-]+)', body)
    if not archive_ids:
        return []

    # 아카이브 API로 실제 다운로드 링크 요청
    archive_id = archive_ids[0]
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await _get(
            client,
            f"https://takeout.googleapis.com/v1/exports/{archive_id}",
            token,
        )
        if response.status_code == 200:
            export_data = response.json()
            files = export_data.get("exportProgress", {}).get("files", [])
            return [f.get("url") for f in files if f.get("url")]

    return []


async def download_from_url(url: str) -> str | None:
    """다운로드 링크에서 ZIP 파일 다운로드"""
    async with httpx.AsyncClient(follow_redirects=True, timeout=300) as client:
        response = await client.get(url)
        if response.status_code != 200:
            return None
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp.write(response.content)
        tmp.close()
        return tmp.name


async def run_takeout_pipeline(zip_path: str):
    """다운로드된 zip → 기존 파싱 파이프라인 실행"""
    from app.agents.indexer.graph import graph

    result = await graph.ainvoke({
        "json_path": zip_path,
        "raw_data": [],
        "cleaned_data": [],
        "error": None,
        "saved_count": None,
        "limit": 500,
    })

    os.unlink(zip_path)
    return result
