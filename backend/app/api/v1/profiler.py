"""Profiler Agent FastAPI 라우터."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.agents.profiler.base import GraphViewData
from app.agents.profiler.scripts.mock_loader import list_personas, load_mock_bundle
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
from app.services.profiler import profiler_compare, profiler_graph_view, profiler_service
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
