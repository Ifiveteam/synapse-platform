from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.agents.profiler.base import GraphViewData
from app.agents.profiler.runtime import job_store
from app.agents.profiler.runtime.insights import (
    build_knowledge_graph,
    build_taste_graph,
    compute_compare_delta,
    compute_ideal_gap,
    detect_anomalies,
    list_snapshot_versions,
    load_snapshot,
    summarize_behavior_events,
)
from app.agents.profiler.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BehaviorEventsResponse,
    CompareResponse,
    IdealGapResponse,
    JobResponse,
    PersonasResponse,
    ProfilerResultResponse,
    SnapshotListResponse,
    SnapshotResponse,
)
from app.agents.profiler.subagent.load_records.loader import (
    list_personas,
    load_mock_bundle,
)

router = APIRouter(prefix="/profiler", tags=["profiler"])


def _to_result_response(result) -> ProfilerResultResponse:
    return ProfilerResultResponse.model_validate(result.model_dump())


def _get_profile_or_404(user_id: str):
    profile = job_store.get_profile(user_id)
    if profile is None:
        snapshot_versions = list_snapshot_versions(user_id)
        if snapshot_versions:
            latest = load_snapshot(user_id, snapshot_versions[-1])
            if latest is not None:
                return latest.result
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

    job = job_store.create_job(body.user_id, str(body.email))
    background_tasks.add_task(job_store.run_job, job.job_id)
    return AnalyzeResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = job_store.get_job(job_id)
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
    delta = compute_compare_delta(user_id, from_snap, to_snap)
    return CompareResponse(delta=delta, anomalies=detect_anomalies(delta))


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
    profile = job_store.get_profile(user_id)
    if kind == "knowledge":
        return build_knowledge_graph(bundle.records)
    return build_taste_graph(bundle.records, profile)


@router.get("/profile/{user_id}/ideal-gap", response_model=IdealGapResponse)
def get_ideal_gap(user_id: str) -> IdealGapResponse:
    profile = _get_profile_or_404(user_id)
    gap = compute_ideal_gap(user_id, profile)
    if gap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ideal profile mock not found for {user_id}",
        )
    return IdealGapResponse(ideal_gap=gap)


@router.get("/profile/{user_id}/events", response_model=BehaviorEventsResponse)
def get_behavior_events(user_id: str) -> BehaviorEventsResponse:
    summary = summarize_behavior_events(user_id)
    if summary.total_events == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No behavior event mock for {user_id}",
        )
    return BehaviorEventsResponse(user_id=user_id, summary=summary)
