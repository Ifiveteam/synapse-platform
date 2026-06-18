"""Profiler Agent FastAPI 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.api.v1.auth import get_current_user_dep
from app.schemas.profiler import (
    AnalysisCompareResponse,
    AnalysisListResponse,
    AnalyzeResponse,
    DbProfileResponse,
    JobResponse,
)
from app.services.profiler.service import profiler_service

router = APIRouter(prefix="/profiler", tags=["profiler"])


def _to_db_profile_response(data: dict) -> DbProfileResponse:
    return DbProfileResponse.model_validate(data)


async def _get_db_profile_or_404(user_id: str) -> DbProfileResponse:
    profile = await profiler_service.fetch_profile_async(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Run POST /profiler/run first.",
        )
    return _to_db_profile_response(profile)


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AnalyzeResponse,
)
def run_profiler_pipeline(
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user_dep),
) -> AnalyzeResponse:
    """인증 유저 catalog → video_summary → profile DB 저장."""
    job = profiler_service.create_job(str(user.id), user.email)
    background_tasks.add_task(profiler_service.run_job_async, job.job_id)
    return AnalyzeResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = profiler_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    result = None
    if job.result:
        result = _to_db_profile_response(job.result)

    return JobResponse(
        job_id=job.job_id,
        user_id=job.user_id,
        status=job.status,
        current_step=job.current_step,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=result,
        error=job.error,
        notification=job.notification,
    )


@router.get("/me/profile", response_model=DbProfileResponse)
async def get_my_profile(user=Depends(get_current_user_dep)) -> DbProfileResponse:
    return await _get_db_profile_or_404(str(user.id))


@router.get("/me/analyses", response_model=AnalysisListResponse)
async def list_my_analyses(user=Depends(get_current_user_dep)) -> AnalysisListResponse:
    """개인성향 분석 목록 — 완료 스냅샷 + 진행 중 job."""
    items = await profiler_service.list_analyses_async(str(user.id))
    return AnalysisListResponse.model_validate({"items": items})


@router.get("/me/analyses/compare", response_model=AnalysisCompareResponse)
async def compare_my_analyses(
    from_snapshot: str = Query(..., alias="from"),
    to_snapshot: str = Query(..., alias="to"),
    user=Depends(get_current_user_dep),
) -> AnalysisCompareResponse:
    """두 완료 스냅샷 비교 (이전 → 이후) — compare 서브 에이전트."""
    if from_snapshot == to_snapshot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from and to must be different snapshots",
        )

    from app.agents.profiler.sub_agent.compare import (
        compare_state_to_api_payload,
        run_compare,
    )

    agent_result = await run_compare(str(user.id), from_snapshot, to_snapshot)
    result = compare_state_to_api_payload(agent_result)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both analysis snapshots not found",
        )
    return AnalysisCompareResponse.model_validate(result)


@router.get("/me/analyses/{snapshot_id}", response_model=DbProfileResponse)
async def get_my_analysis_snapshot(
    snapshot_id: str, user=Depends(get_current_user_dep)
) -> DbProfileResponse:
    profile = await profiler_service.fetch_snapshot_async(str(user.id), snapshot_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis snapshot not found",
        )
    return _to_db_profile_response(profile)


@router.get("/profile/{user_id}", response_model=DbProfileResponse)
async def get_profile(user_id: str) -> DbProfileResponse:
    return await _get_db_profile_or_404(user_id)


_video_summary_status: dict[str, dict] = {}


async def _run_video_summary_task(
    task_id: str, user_id: uuid.UUID, limit: int | None
) -> None:
    from app.agents.profiler.sub_agent import run_video_summary

    _video_summary_status[task_id] = {"status": "running", "user_id": str(user_id)}
    try:
        result = await run_video_summary(user_id, limit)
        _video_summary_status[task_id] = {
            "status": "completed",
            "user_id": str(user_id),
            "saved_count": result.get("saved_count"),
            "skipped_count": result.get("skipped_count"),
            "fetched": len(result.get("catalogs") or []),
            "error": result.get("error"),
        }
    except Exception as e:  # noqa: BLE001
        _video_summary_status[task_id] = {
            "status": "failed",
            "user_id": str(user_id),
            "error": str(e),
        }


@router.post("/video-summary/run", status_code=status.HTTP_202_ACCEPTED)
async def run_video_summary_endpoint(
    background_tasks: BackgroundTasks,
    limit: int | None = Query(None, ge=1),
    user=Depends(get_current_user_dep),
) -> dict:
    """현재 유저 catalog 샘플 → video_analysis 적재."""
    task_id = str(uuid.uuid4())
    _video_summary_status[task_id] = {"status": "queued", "user_id": str(user.id)}
    background_tasks.add_task(_run_video_summary_task, task_id, user.id, limit)
    return {"status": "started", "task_id": task_id}


@router.get("/video-summary/{task_id}")
async def get_video_summary_status(task_id: str) -> dict:
    info = _video_summary_status.get(task_id)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown task_id"
        )
    return {"task_id": task_id, **info}
