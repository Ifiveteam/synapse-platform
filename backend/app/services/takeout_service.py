from __future__ import annotations

import os
import tempfile
import uuid

import httpx


async def _get(
    client: httpx.AsyncClient, url: str, token: str, **kwargs
) -> httpx.Response:
    response = await client.get(
        url, headers={"Authorization": f"Bearer {token}"}, **kwargs
    )
    if response.status_code == 401:
        return response
    return response


async def refresh_user_token(user) -> str | None:
    """user_token의 구글 refresh_token으로 access_token 갱신 후 DB 저장.

    OAuth 로직은 services/google_oauth로 일원화. 이 함수는 호환용 위임.
    """
    from app.services.google_oauth import refresh_access_token

    return await refresh_access_token(user)


_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


async def _list_takeout_files(user, q: str) -> list[dict]:
    """주어진 Drive 쿼리로 Takeout 파일 목록 조회 (401 시 토큰 갱신)."""
    token = user.access_token
    if not token:
        return []

    params = {
        "q": q,
        "orderBy": "modifiedTime desc",
        "fields": "files(id,name,size,modifiedTime,mimeType)",
        "pageSize": 50,
    }

    async with httpx.AsyncClient() as client:
        response = await _get(client, _DRIVE_FILES_URL, token, params=params)

    if response.status_code == 401:
        token = await refresh_user_token(user)
        if not token:
            return []
        async with httpx.AsyncClient() as client:
            response = await _get(client, _DRIVE_FILES_URL, token, params=params)

    if response.status_code != 200:
        print(f"[Drive] 파일 조회 실패: {response.status_code} {response.text}")
        return []

    files = response.json().get("files", [])
    # archive_browser.html만 있는 빈 ZIP 제외 (200KB 미만)
    files = [f for f in files if int(f.get("size", 0)) >= 200 * 1024]
    return files


async def find_takeout_in_folder(user, folder_id: str) -> list[dict]:
    """연동된 폴더 안에서만 Takeout ZIP 검색 (drive.file 스코프)."""
    if not folder_id:
        return []
    q = (
        f"'{folder_id}' in parents and name contains 'takeout' "
        "and mimeType != 'application/vnd.google-apps.folder' and trashed=false"
    )
    files = await _list_takeout_files(user, q)
    print(
        f"[Drive] 폴더 {folder_id[:12]}… 검색 {len(files)}개: "
        f"{[f['name'] for f in files]}"
    )
    return files


async def download_drive_file(file_id: str, user) -> str | None:
    """Drive 파일 스트리밍 다운로드 → 임시 파일 경로 반환"""
    token = user.access_token
    if not token:
        return None

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    params = {"alt": "media", "acknowledgeAbuse": "true"}
    headers = {"Authorization": f"Bearer {token}"}

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=600) as client:
            async with client.stream(
                "GET", url, headers=headers, params=params
            ) as response:
                if response.status_code == 401:
                    token = await refresh_user_token(user)
                    if not token:
                        return None
                    headers = {"Authorization": f"Bearer {token}"}

                if response.status_code == 401:
                    print("[Drive] 토큰 갱신 후에도 401")
                    return None

                if response.status_code != 200:
                    body = await response.aread()
                    print(f"[Drive] 다운로드 실패: {response.status_code} {body[:200]}")
                    return None

                total = 0
                async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                    tmp.write(chunk)
                    total += len(chunk)
                print(
                    f"[Drive] 다운로드 완료: {total / 1024 / 1024:.1f} MB → {tmp.name}"
                )
    finally:
        tmp.close()

    return tmp.name


async def run_takeout_pipeline(
    file_path: str, user_id: uuid.UUID | None = None
) -> dict:
    """ZIP 또는 JSON 파일 → Indexer pipeline 실행"""
    from collections import Counter

    from app.agents.indexer.graph import graph

    result = await graph.ainvoke(
        {
            "json_path": file_path,
            "raw_data": [],
            "cleaned_data": [],
            "error": None,
            "saved_count": None,
            "user_id": user_id,
        }
    )

    try:
        os.unlink(file_path)
    except OSError:
        pass

    cleaned = result.get("cleaned_data", [])
    shorts_count = sum(1 for item in cleaned if item.get("is_shorts"))
    category_stats = dict(
        Counter(
            str(item.get("youtube_category_id") or "unknown") for item in cleaned
        ).most_common()
    )

    return {
        **result,
        "raw_count": len(result.get("raw_data", [])),
        "filtered_count": result.get("filtered_count") or len(cleaned),
        "cleaned_count": len(cleaned),
        "shorts_count": shorts_count,
        "category_stats": category_stats,
        "subscription_count": result.get("subscription_saved") or 0,
    }
