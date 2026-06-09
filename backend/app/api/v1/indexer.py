import os
import tempfile
import uuid
from collections import Counter

from fastapi import APIRouter, BackgroundTasks, File, UploadFile

from app.agents.indexer.graph import graph

router = APIRouter(prefix="/indexer", tags=["indexer"])

analysis_status: dict = {}


def run_analysis(task_id: str, tmp_path: str, limit: int = 100):
    """백그라운드 분석 실행"""
    try:
        analysis_status[task_id] = {"status": "running"}

        result = graph.invoke(
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


@router.get("/status")
def status():
    """인덱서 상태 확인"""
    return {"status": "running"}