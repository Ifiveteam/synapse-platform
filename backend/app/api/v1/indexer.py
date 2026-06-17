import os
import tempfile
import uuid as uuid_mod
from collections import Counter
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.indexer.graph import graph
from app.api.v1.auth import get_current_user_dep
from app.core.database.session import get_db

router = APIRouter(prefix="/indexer", tags=["indexer"])

analysis_status: dict = {}


def _temp_upload_path(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".zip", ".json"}:
        suffix = ".json"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        return tmp.name


async def run_analysis(
    task_id: str,
    tmp_path: str,
    user_id: UUID,
):
    """백그라운드 분석 실행"""
    try:
        analysis_status[task_id] = {"status": "running"}

        result = await graph.ainvoke(
            {
                "json_path": tmp_path,
                "raw_data": [],
                "cleaned_data": [],
                "error": None,
                "saved_count": None,
                "user_id": user_id,
            }
        )

        os.unlink(tmp_path)

        if result["error"]:
            analysis_status[task_id] = {"status": "error", "message": result["error"]}
            return

        cleaned = result.get("cleaned_data") or []
        category_stats = dict(
            Counter(
                str(item.get("youtube_category_id") or "unknown") for item in cleaned
            ).most_common()
        )
        shorts_count = sum(1 for item in cleaned if item.get("is_shorts"))

        analysis_status[task_id] = {
            "status": "success",
            "total": len(result.get("raw_data") or []),
            "processed": result.get("saved_count"),
            "raw_count": len(result.get("raw_data") or []),
            "filtered_count": result.get("filtered_count") or len(cleaned),
            "cleaned_count": len(cleaned),
            "shorts_count": shorts_count,
            "category_stats": category_stats,
        }

        if result.get("saved_count"):
            from app.services.profiler.service import profiler_service

            profiler_service.enqueue_for_user(str(user_id))
    except Exception as e:
        analysis_status[task_id] = {"status": "error", "message": str(e)}


@router.post("/analyze")
async def analyze(  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
    user=Depends(get_current_user_dep),
):
    """테이크아웃 JSON 파일 업로드 → 백그라운드 분석 시작"""
    tmp_path = _temp_upload_path(file)
    content = await file.read()
    with open(tmp_path, "wb") as tmp:
        tmp.write(content)

    task_id = str(uuid_mod.uuid4())
    background_tasks.add_task(run_analysis, task_id, tmp_path, user.id)

    return {"status": "started", "task_id": task_id}


@router.post("/analyze/sample")
async def analyze_sample(  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
    user=Depends(get_current_user_dep),
):
    """샘플 모드 - 20개만 처리 (시연용)"""
    tmp_path = _temp_upload_path(file)
    content = await file.read()
    with open(tmp_path, "wb") as tmp:
        tmp.write(content)

    task_id = str(uuid_mod.uuid4())
    background_tasks.add_task(run_analysis, task_id, tmp_path, user.id)

    return {"status": "started", "task_id": task_id, "mode": "sample"}


@router.get("/analyze/{task_id}")
def get_result(task_id: str):
    """분석 결과 조회"""
    if task_id not in analysis_status:
        return {"status": "not_found"}
    return analysis_status[task_id]


@router.get("/videos")
async def get_videos(
    session: AsyncSession = Depends(get_db), user=Depends(get_current_user_dep)
):
    """수집된 영상 목록 조회 (최신순, 본인 데이터만)"""
    from app.repositories.indexer_repository import get_all_catalog

    videos = await get_all_catalog(session, user_id=user.id)
    return [
        {
            "id": str(v.id),
            "title": v.title or "",
            "channel": v.channel,
            "url": v.url,
            "watched_at": str(v.watched_at) if v.watched_at else "",
            "youtube_category_id": v.youtube_category_id or "",
            "tags": v.tags if isinstance(v.tags, list) else [],
            "duration": v.duration_sec or 0,
            "is_shorts": v.is_shorts or False,
            "thumbnail_url": v.thumbnail_url or "",
        }
        for v in videos
    ]


@router.delete("/videos")
async def delete_all_videos(
    session: AsyncSession = Depends(get_db), user=Depends(get_current_user_dep)
):
    """본인 catalog + 분석 결과 전체 삭제"""
    from app.repositories.indexer_repository import delete_user_catalog

    await delete_user_catalog(session, user.id)
    await session.commit()
    return {"message": "전체 삭제 완료"}


@router.get("/status")
def status():
    """인덱서 상태 확인"""
    return {"status": "running"}
