import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user_dep
from app.core.database.session import get_db
from app.models.user import User
from app.repositories.analysis_source_repository import begin_source
from app.services.analysis_source_service import drive_source_key, fail_source_async
from app.services.takeout_service import (
    download_drive_file,
    find_takeout_in_drive,
    run_takeout_pipeline,
)

router = APIRouter(prefix="/takeout", tags=["takeout"])

takeout_status: dict = {}


async def _enqueue_profiler(user: User, analysis_source_id: str) -> None:
    from app.services.profiler.service import profiler_service

    profiler_service.enqueue_for_user(
        str(user.id),
        user.email,
        analysis_source_id=analysis_source_id,
    )


async def run_drive_takeout(
    task_id: str, file_id: str, user: User, analysis_source_id: str
) -> None:
    try:
        takeout_status[task_id] = {"status": "downloading"}

        file_path = await download_drive_file(file_id, user)
        if not file_path:
            takeout_status[task_id] = {
                "status": "error",
                "message": "Drive 파일 다운로드 실패",
            }
            await fail_source_async(analysis_source_id)
            return

        takeout_status[task_id] = {"status": "processing"}
        result = await run_takeout_pipeline(file_path, user_id=user.id)

        if result.get("error"):
            print(f"[Pipeline] 오류: {result['error']}")
            takeout_status[task_id] = {"status": "error", "message": result["error"]}
            await fail_source_async(analysis_source_id)
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

        await _enqueue_profiler(user, analysis_source_id)
    except Exception as e:
        print(f"[Drive] 태스크 오류 ({task_id}): {e}")
        takeout_status[task_id] = {"status": "error", "message": str(e)}
        await fail_source_async(analysis_source_id)


@router.get("/drive/files")
async def list_drive_files(user: User = Depends(get_current_user_dep)):
    files = await find_takeout_in_drive(user)
    return {"files": files}


@router.post("/drive/auto")
async def auto_trigger(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    """Drive에서 최신 Takeout 파일 자동 탐지 후 분석 시작"""
    files = await find_takeout_in_drive(user)
    if not files:
        return {"status": "no_files"}

    latest = sorted(files, key=lambda f: f.get("modifiedTime", ""), reverse=True)[0]
    return await _trigger_drive_file(
        latest["id"], latest.get("name"), background_tasks, user, session
    )


@router.post("/drive/trigger/{file_id}")
async def trigger_drive_file(
    file_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    files = await find_takeout_in_drive(user)
    match = next((f for f in files if f.get("id") == file_id), None)
    file_name = match.get("name") if match else None
    return await _trigger_drive_file(
        file_id, file_name, background_tasks, user, session
    )


async def _trigger_drive_file(
    file_id: str,
    file_name: str | None,
    background_tasks: BackgroundTasks,
    user: User,
    session: AsyncSession,
) -> dict:
    source_key = drive_source_key(file_id)
    row, action = await begin_source(session, user.id, source_key, file_name)
    await session.commit()

    if action == "skip_completed":
        return {
            "status": "already_completed",
            "profile_history_id": (
                str(row.profile_history_id) if row.profile_history_id else None
            ),
        }
    if action == "skip_running":
        return {"status": "already_running"}

    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_drive_takeout, task_id, file_id, user, str(row.id))
    return {"status": "started", "task_id": task_id}


@router.get("/status/{task_id}")
def get_status(task_id: str):
    return takeout_status.get(task_id, {"status": "not_found"})
