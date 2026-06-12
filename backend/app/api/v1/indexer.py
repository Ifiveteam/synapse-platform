import os
import tempfile
import uuid
from collections import Counter

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.indexer.graph import graph
from app.agents.indexer.graph_extension import extension_graph
from app.core.database.session import get_db

router = APIRouter(prefix="/indexer", tags=["indexer"])

analysis_status: dict = {}


class VideoTrackRequest(BaseModel):
    title: str
    channel: str
    channel_url: str = ""
    url: str
    watched_at: str
    duration: int = 0
    is_shorts: bool = False


async def run_analysis(task_id: str, tmp_path: str, limit: int = 100):
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
                "limit": limit,
            }
        )

        os.unlink(tmp_path)

        if result["error"]:
            analysis_status[task_id] = {"status": "error", "message": result["error"]}
            return

        categories = [item.get("category", "") for item in result["cleaned_data"]]
        category_stats = dict(Counter(categories).most_common())

        videos = [
            {
                "title": item.get("title", ""),
                "channel": item.get("channel", ""),
                "category": item.get("category", ""),
                "watched_at": item.get("watched_at", ""),
                "keywords": item.get("keywords", []),
                "duration": item.get("duration", 0),
                "is_shorts": item.get("is_shorts", False),
            }
            for item in result["cleaned_data"]
        ]

        analysis_status[task_id] = {
            "status": "success",
            "total": len(result["raw_data"]),
            "processed": result["saved_count"],
            "category_stats": category_stats,
            "videos": videos,
        }
    except Exception as e:
        analysis_status[task_id] = {"status": "error", "message": str(e)}


@router.post("/analyze")
async def analyze(  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
):
    """테이크아웃 JSON 파일 업로드 → 백그라운드 분석 시작"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_analysis, task_id, tmp_path, 100)

    return {"status": "started", "task_id": task_id}


@router.post("/analyze/sample")
async def analyze_sample(  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
):
    """샘플 모드 - 20개만 처리 (시연용)"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_analysis, task_id, tmp_path, 20)

    return {"status": "started", "task_id": task_id, "mode": "sample"}


@router.get("/analyze/{task_id}")
def get_result(task_id: str):
    """분석 결과 조회"""
    if task_id not in analysis_status:
        return {"status": "not_found"}
    return analysis_status[task_id]


@router.get("/videos")
async def get_videos(session: AsyncSession = Depends(get_db)):
    """수집된 영상 목록 조회"""
    from app.agents.indexer.repository import get_all_videos

    videos = await get_all_videos(session)
    return [
        {
            "id": v.id,
            "title": v.title,
            "channel": v.channel,
            "url": v.url,
            "watched_at": str(v.watched_at) if v.watched_at else "",
            "category": v.category or "",
            "keywords": v.keywords or [],
            "duration": v.duration or 0,
            "is_shorts": v.is_shorts or False,
        }
        for v in videos
    ]


@router.delete("/videos")
async def delete_all_videos(session: AsyncSession = Depends(get_db)):
    """수집된 영상 전체 삭제"""
    from app.models.video_vector import VideoVector
    await session.execute(delete(VideoVector))
    await session.commit()
    return {"message": "전체 삭제 완료"}


@router.get("/status")
def status():
    """인덱서 상태 확인"""
    return {"status": "running"}


async def run_extension_analysis(task_id: str, video: dict):
    """익스텐션 단일 영상 백그라운드 처리"""
    try:
        analysis_status[task_id] = {"status": "running"}
        result = await extension_graph.ainvoke({
            "videos": [video],
            "cleaned_data": [],
            "error": None,
            "saved_count": None,
        })
        if result["error"]:
            analysis_status[task_id] = {"status": "error", "message": result["error"]}
            return
        analysis_status[task_id] = {
            "status": "success",
            "saved": result["saved_count"],
        }
    except Exception as e:
        analysis_status[task_id] = {"status": "error", "message": str(e)}


@router.post("/track")
async def track_video(
    video: VideoTrackRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
):
    """익스텐션에서 실시간 영상 수집"""
    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_extension_analysis, task_id, video.model_dump())
    return {"status": "started", "task_id": task_id}
