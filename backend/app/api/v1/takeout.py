import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user_dep
from app.core.database.session import get_db
from app.models.user import User
from app.models.user_analysis_source import AnalysisSourceStage
from app.models.user_token import UserToken
from app.repositories.analysis_source_repository import begin_source
from app.schemas.auth import DriveConnectionResponse, DriveFolderRequest
from app.services.analysis_source_service import (
    drive_source_key,
    fail_source_async,
    set_source_stage_async,
)
from app.services.takeout_service import (
    download_drive_file,
    find_takeout_in_folder,
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
        await set_source_stage_async(analysis_source_id, AnalysisSourceStage.PROFILING)
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


async def _get_user_token(session: AsyncSession, user: User) -> UserToken | None:
    result = await session.execute(
        select(UserToken).where(UserToken.user_id == user.id)
    )
    return result.scalar_one_or_none()


@router.post("/drive/folder")
async def save_drive_folder(
    body: DriveFolderRequest,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    """Picker로 선택한 감시 폴더를 저장 (연동 완료)."""
    from datetime import datetime, timezone

    from app.services.takeout_scheduler import first_of_month_ahead

    token_row = await _get_user_token(session, user)
    if token_row is None:
        return {"status": "no_token"}  # /auth/drive/connect 먼저 필요
    token_row.drive_folder_id = body.folder_id
    token_row.drive_folder_name = body.folder_name
    # 연동 직후 즉시 실행 방지 — 다음 달 1일부터 스케줄 시작
    now = datetime.now(timezone.utc)
    if user.next_analysis_at is None or user.next_analysis_at <= now:
        user.next_analysis_at = first_of_month_ahead(now, 1)
    await session.commit()
    return {"status": "saved", "folder_name": body.folder_name}


@router.get("/drive/connection", response_model=DriveConnectionResponse)
async def drive_connection(
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> DriveConnectionResponse:
    """폴더 연동 여부 + 폴더명."""
    token_row = await _get_user_token(session, user)
    connected = bool(token_row and token_row.drive_folder_id)
    return DriveConnectionResponse(
        connected=connected,
        folder_name=token_row.drive_folder_name if token_row else None,
    )


async def _folder_files(session: AsyncSession, user: User) -> list[dict]:
    token_row = await _get_user_token(session, user)
    if not token_row or not token_row.drive_folder_id:
        return []
    return await find_takeout_in_folder(user, token_row.drive_folder_id)


@router.get("/drive/files")
async def list_drive_files(
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    """연동 폴더의 Takeout 파일 목록 + 파일별 분석 상태.

    status: new(미분석) | running(분석중) | completed(분석됨) | failed(실패)
    """
    from app.repositories.analysis_source_repository import (
        fetch_user_source_status_map,
    )

    files = await _folder_files(session, user)
    status_map = await fetch_user_source_status_map(session, user.id)
    items = [
        {
            "id": f["id"],
            "name": f.get("name"),
            "modified_time": f.get("modifiedTime"),
            "status": status_map.get(drive_source_key(f["id"]), "new"),
        }
        for f in files
    ]
    # 최신 수정순 정렬
    items.sort(key=lambda f: f.get("modified_time") or "", reverse=True)
    return {"files": items}


@router.post("/drive/auto")
async def auto_trigger(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    """연동 폴더에서 최신 Takeout 파일 자동 탐지 후 분석 시작"""
    files = await _folder_files(session, user)
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
    files = await _folder_files(session, user)
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
