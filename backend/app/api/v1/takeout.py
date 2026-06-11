import uuid

from fastapi import APIRouter, BackgroundTasks

from app.services.takeout_service import (
    download_from_url,
    find_takeout_email,
    get_download_links_from_email,
    run_takeout_pipeline,
)

router = APIRouter(prefix="/takeout", tags=["takeout"])

takeout_status: dict = {}


async def run_auto_takeout(task_id: str):
    """Gmail 감지 → 링크 추출 → 다운로드 → 파이프라인 실행"""
    takeout_status[task_id] = {"status": "gmail_checking"}

    email = await find_takeout_email()
    if not email:
        takeout_status[task_id] = {"status": "no_email", "message": "테이크아웃 메일 없음"}
        return

    takeout_status[task_id] = {"status": "extracting_links"}
    links = await get_download_links_from_email(email["id"])
    if not links:
        takeout_status[task_id] = {"status": "no_links", "message": "다운로드 링크 없음"}
        return

    takeout_status[task_id] = {"status": "downloading"}
    zip_path = await download_from_url(links[0])
    if not zip_path:
        takeout_status[task_id] = {"status": "download_failed"}
        return

    takeout_status[task_id] = {"status": "processing"}
    result = await run_takeout_pipeline(zip_path)

    if result.get("error"):
        takeout_status[task_id] = {"status": "error", "message": result["error"]}
        return

    takeout_status[task_id] = {
        "status": "success",
        "saved": result.get("saved_count", 0),
    }


@router.post("/trigger")
async def trigger_takeout(background_tasks: BackgroundTasks):
    """Gmail 감지 → 링크 추출 → 다운로드 트리거"""
    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_auto_takeout, task_id)
    return {"status": "started", "task_id": task_id}


@router.get("/status/{task_id}")
def get_status(task_id: str):
    return takeout_status.get(task_id, {"status": "not_found"})


@router.get("/debug-archive")
async def debug_archive():
    """Takeout 아카이브 페이지 접근 테스트"""
    from app.services.takeout_service import get_access_token
    import httpx, re

    token = await get_access_token()
    if not token:
        return {"error": "토큰 없음"}

    url = "https://takeout.google.com/manage/archive/97dc4fb7-ea23-4acd-b411-e9b903cd1b9f"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0",
            },
        )
        body = response.text
        links = re.findall(r'https://[^\s"\'<>]+\.zip[^\s"\'<>]*', body)
        storage_links = re.findall(r'https://storage\.googleapis\.com[^\s"\'<>]+', body)
        takeout_links = re.findall(r'https://takeout-export[^\s"\'<>]+', body)

    return {
        "status_code": response.status_code,
        "zip_links": links[:10],
        "storage_links": storage_links[:10],
        "takeout_links": takeout_links[:10],
        "body_preview": body[:500],
    }


@router.get("/debug-body")
async def debug_body():
    """메일 본문 링크 확인 (디버그용)"""
    from app.services.takeout_service import find_takeout_email, get_access_token
    import httpx, base64, re

    token = await get_access_token()
    email = await find_takeout_email()
    if not email:
        return {"error": "메일 없음"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{email['id']}",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "full"},
        )
        data = response.json()

    body = ""
    payload = data.get("payload", {})
    parts = payload.get("parts", [payload])
    for part in parts:
        if part.get("mimeType") in ("text/html", "text/plain"):
            encoded = part.get("body", {}).get("data", "")
            if encoded:
                body += base64.urlsafe_b64decode(encoded + "==").decode("utf-8", errors="ignore")

    links = re.findall(r'https://[^\s"<>]+', body)
    google_links = [l for l in links if "google" in l.lower()]
    return {"google_links": google_links[:20], "body_length": len(body)}


@router.get("/debug")
async def debug_takeout():
    """최근 Google 메일 목록 확인 (디버그용)"""
    from app.services.takeout_service import get_access_token
    import httpx

    token = await get_access_token()
    if not token:
        return {"error": "토큰 없음"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": "from:google.com newer_than:30d", "maxResults": 10},
        )
        messages = response.json().get("messages", [])

        results = []
        for msg in messages[:5]:
            detail = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}?format=metadata&metadataHeaders=subject&metadataHeaders=from",
                headers={"Authorization": f"Bearer {token}"},
            )
            headers = {h["name"].lower(): h["value"] for h in detail.json().get("payload", {}).get("headers", [])}
            results.append({"subject": headers.get("subject"), "from": headers.get("from")})

    return {"emails": results}


@router.get("/check")
async def check_takeout():
    """테이크아웃 메일 있는지 확인"""
    email = await find_takeout_email()
    links = []
    if email:
        links = await get_download_links_from_email(email["id"])
    return {
        "email_found": email is not None,
        "download_links_found": len(links),
    }
