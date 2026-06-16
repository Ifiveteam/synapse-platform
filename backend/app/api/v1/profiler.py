"""Profiler Agent FastAPI 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.agents.profiler.base import GraphViewData
from app.agents.profiler.scripts.mock_loader import list_personas, load_mock_bundle
from app.api.v1.auth import get_current_user_dep
from app.schemas.profiler import (
    AnalyzeRequest,
    AnalyzeResponse,
    CompareResponse,
    JobResponse,
    PersonasResponse,
    ProfilerResultResponse,
    SnapshotListResponse,
    SnapshotResponse,
)
from app.services.profiler import (
    profiler_compare,
    profiler_graph_view,
    profiler_service,
)
from app.services.profiler.service import list_snapshot_versions, load_snapshot

router = APIRouter(prefix="/profiler", tags=["profiler"])


def _to_result_response(result) -> ProfilerResultResponse:
    return ProfilerResultResponse.model_validate(result.model_dump())


def _get_profile_or_404(user_id: str):
    profile = profiler_service.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Run POST /analyze first.",
        )
    return profile


@router.post(
    "/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AnalyzeResponse,
)
def analyze_profile(
    body: AnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> AnalyzeResponse:
    known_ids = {persona.id for persona in list_personas()}
    if body.user_id not in known_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown user_id: {body.user_id}. Use GET /personas for mock ids.",
        )

    job = profiler_service.create_job(body.user_id, str(body.email))
    background_tasks.add_task(profiler_service.run_job, job.job_id)
    return AnalyzeResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = profiler_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobResponse(
        job_id=job.job_id,
        user_id=job.user_id,
        status=job.status,
        current_step=job.current_step,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=_to_result_response(job.result) if job.result else None,
        error=job.error,
        notification=job.notification,
    )


@router.get("/profile/{user_id}", response_model=ProfilerResultResponse)
def get_profile(user_id: str) -> ProfilerResultResponse:
    return _to_result_response(_get_profile_or_404(user_id))


@router.get("/personas", response_model=PersonasResponse)
def get_personas() -> PersonasResponse:
    return PersonasResponse(personas=list_personas())


@router.get("/profile/{user_id}/snapshots", response_model=SnapshotListResponse)
def get_snapshots(user_id: str) -> SnapshotListResponse:
    return SnapshotListResponse(
        user_id=user_id, versions=list_snapshot_versions(user_id)
    )


@router.get("/profile/{user_id}/snapshots/{version}", response_model=SnapshotResponse)
def get_snapshot(user_id: str, version: str) -> SnapshotResponse:
    snapshot = load_snapshot(user_id, version)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot {version} not found for {user_id}",
        )
    return SnapshotResponse(snapshot=snapshot)


@router.get("/profile/{user_id}/compare", response_model=CompareResponse)
def compare_profiles(
    user_id: str,
    from_version: str = Query(..., alias="from"),
    to_version: str = Query(..., alias="to"),
) -> CompareResponse:
    from_snap = load_snapshot(user_id, from_version)
    to_snap = load_snapshot(user_id, to_version)
    if from_snap is None or to_snap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both snapshot versions not found",
        )
    delta = profiler_compare.compute_compare_delta(user_id, from_snap, to_snap)
    return CompareResponse(
        delta=delta, anomalies=profiler_compare.detect_anomalies(delta)
    )


@router.get("/profile/{user_id}/graph", response_model=GraphViewData)
def get_graph(
    user_id: str,
    kind: str = Query("taste", pattern="^(taste|knowledge)$"),
) -> GraphViewData:
    try:
        bundle = load_mock_bundle(user_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    profile = profiler_service.get_profile(user_id)
    return profiler_graph_view.build_graph(bundle.records, profile, kind)


# ── 영상요약 서브에이전트 (DB 기반, ERD 파이프라인) ──────────────
# 기존 목(mock) 엔드포인트와 분리된 /video-summary 네임스페이스.

_video_summary_status: dict[str, dict] = {}


async def _run_video_summary_task(
    task_id: str, user_id: uuid.UUID, limit: int | None
) -> None:
    from app.agents.profiler.video_summary import run_video_summary

    _video_summary_status[task_id] = {"status": "running", "user_id": str(user_id)}
    try:
        result = await run_video_summary(user_id, limit)
        _video_summary_status[task_id] = {
            "status": "completed",
            "user_id": str(user_id),
            "saved_count": result.get("saved_count"),
            "skipped_count": result.get("skipped_count"),
            "fetched": len(result.get("watches") or []),
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
    """현재 유저의 user_video_watch를 영상요약 분석해 video_analysis에 적재."""
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
