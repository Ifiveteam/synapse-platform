import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.v1.auth import get_current_user_dep
from app.models.user import User
from app.services.takeout_service import (
    download_drive_file,
    find_takeout_in_drive,
    run_takeout_pipeline,
)

router = APIRouter(prefix="/takeout", tags=["takeout"])

takeout_status: dict = {}


async def run_drive_takeout(task_id: str, file_id: str, user: User) -> None:
    try:
        takeout_status[task_id] = {"status": "downloading"}

        file_path = await download_drive_file(file_id, user)
        if not file_path:
            takeout_status[task_id] = {
                "status": "error",
                "message": "Drive 파일 다운로드 실패",
            }
            return

        takeout_status[task_id] = {"status": "processing"}
        result = await run_takeout_pipeline(file_path, user_id=user.id)

        if result.get("error"):
            print(f"[Pipeline] 오류: {result['error']}")
            takeout_status[task_id] = {"status": "error", "message": result["error"]}
            return

        saved = result.get("saved_count", 0)
        print(
            f"[Pipeline] 완료: {saved}개 저장됨 (원본 {result.get('raw_count', 0)}개 파싱)"
        )
        takeout_status[task_id] = {
            "status": "success",
            "saved": saved,
            "raw_count": result.get("raw_count", 0),
            "filtered_count": result.get("filtered_count", 0),
            "cleaned_count": result.get("cleaned_count", 0),
            "shorts_count": result.get("shorts_count", 0),
            "category_stats": result.get("category_stats", {}),
        }
    except Exception as e:
        print(f"[Drive] 태스크 오류 ({task_id}): {e}")
        takeout_status[task_id] = {"status": "error", "message": str(e)}


@router.get("/drive/files")
async def list_drive_files(user: User = Depends(get_current_user_dep)):
    files = await find_takeout_in_drive(user)
    return {"files": files}


@router.post("/drive/auto")
async def auto_trigger(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dep),
):
    """Drive에서 최신 Takeout 파일 자동 탐지 후 분석 시작"""
    files = await find_takeout_in_drive(user)
    if not files:
        return {"status": "no_files"}

    latest = sorted(files, key=lambda f: f.get("modifiedTime", ""), reverse=True)[0]
    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_drive_takeout, task_id, latest["id"], user)
    return {
        "status": "started",
        "task_id": task_id,
        "file_id": latest["id"],
        "file_name": latest["name"],
    }


@router.post("/drive/trigger/{file_id}")
async def trigger_drive_file(
    file_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dep),
):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_drive_takeout, task_id, file_id, user)
    return {"status": "started", "task_id": task_id}


@router.get("/status/{task_id}")
def get_status(task_id: str):
    return takeout_status.get(task_id, {"status": "not_found"})
