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
from app.models.user_analysis_source import AnalysisSourceStage
from app.repositories.analysis_source_repository import begin_source
from app.services.analysis_source_service import (
    fail_source_async,
    set_source_stage_async,
    upload_source_key,
)

router = APIRouter(prefix="/indexer", tags=["indexer"])

analysis_status: dict = {}


def _temp_upload_path(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".zip", ".json"}:
        suffix = ".json"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        return tmp.name


async def _enqueue_profiler(
    user_id: UUID, user_email: str, analysis_source_id: str
) -> None:
    from app.services.profiler.service import profiler_service

    profiler_service.enqueue_for_user(
        str(user_id),
        user_email,
        analysis_source_id=analysis_source_id,
    )


async def run_analysis(
    task_id: str,
    tmp_path: str,
    user_id: UUID,
    user_email: str,
    analysis_source_id: str,
):
    """백그라운드 분석 실행 — 인덱서 후 프로파일러 자동 큐."""
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
            await fail_source_async(analysis_source_id)
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

        await set_source_stage_async(analysis_source_id, AnalysisSourceStage.PROFILING)
        await _enqueue_profiler(user_id, user_email, analysis_source_id)
    except Exception as e:
        analysis_status[task_id] = {"status": "error", "message": str(e)}
        await fail_source_async(analysis_source_id)


async def _start_upload_analysis(
    *,
    session: AsyncSession,
    background_tasks: BackgroundTasks,
    user,
    content: bytes,
    filename: str | None,
    tmp_path: str,
    mode: str | None = None,
) -> dict:
    source_key = upload_source_key(content)
    row, action = await begin_source(session, user.id, source_key, filename)
    await session.commit()

    if action == "skip_completed":
        os.unlink(tmp_path)
        return {
            "status": "already_completed",
            "profile_history_id": (
                str(row.profile_history_id) if row.profile_history_id else None
            ),
        }
    if action == "skip_running":
        os.unlink(tmp_path)
        return {"status": "already_running"}

    task_id = str(uuid_mod.uuid4())
    background_tasks.add_task(
        run_analysis,
        task_id,
        tmp_path,
        user.id,
        user.email,
        str(row.id),
    )
    payload = {"status": "started", "task_id": task_id}
    if mode:
        payload["mode"] = mode
    return payload


@router.post("/analyze")
async def analyze(  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
    user=Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    """테이크아웃 JSON 파일 업로드 → 백그라운드 분석 시작"""
    tmp_path = _temp_upload_path(file)
    content = await file.read()
    with open(tmp_path, "wb") as tmp:
        tmp.write(content)

    return await _start_upload_analysis(
        session=session,
        background_tasks=background_tasks,
        user=user,
        content=content,
        filename=file.filename,
        tmp_path=tmp_path,
    )


@router.post("/analyze/sample")
async def analyze_sample(  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
    user=Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    """샘플 모드 - 20개만 처리 (시연용)"""
    tmp_path = _temp_upload_path(file)
    content = await file.read()
    with open(tmp_path, "wb") as tmp:
        tmp.write(content)

    return await _start_upload_analysis(
        session=session,
        background_tasks=background_tasks,
        user=user,
        content=content,
        filename=file.filename,
        tmp_path=tmp_path,
        mode="sample",
    )


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


@router.get("/graph-summary")
async def get_graph_summary(
    session: AsyncSession = Depends(get_db), user=Depends(get_current_user_dep)
):
    """시청 그래프 UI용 catalog 집계 (상위 카테고리·채널, 경량)."""
    from app.repositories.indexer_repository import fetch_graph_summary

    return await fetch_graph_summary(session, user.id)


@router.get("/embedding-graph")
async def get_embedding_graph(
    before: str | None = None,
    after: str | None = None,
    session: AsyncSession = Depends(get_db),
    user=Depends(get_current_user_dep),
):
    """영상별 임베딩 PCA 2D 투영 그래프. before/after: ISO 날짜 문자열 (선택)."""
    from datetime import datetime, timezone

    from app.repositories.indexer_repository import fetch_catalog_embedding_rows
    from app.services.catalog_embedding_graph import build_embedding_graph_payload

    def _parse(s: str | None):
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    rows = await fetch_catalog_embedding_rows(
        session, user.id, before=_parse(before), after=_parse(after)
    )
    return build_embedding_graph_payload(rows)


@router.delete("/videos")
async def delete_all_videos(
    session: AsyncSession = Depends(get_db), user=Depends(get_current_user_dep)
):
    """본인 catalog + 분석 결과 + 구독 + 소스 이력 전체 삭제"""
    from app.repositories.analysis_source_repository import delete_sources_for_user
    from app.repositories.indexer_repository import (
        delete_subscriptions,
        delete_user_catalog,
    )

    await delete_user_catalog(session, user.id)
    await delete_subscriptions(session, user.id)
    await delete_sources_for_user(session, user.id)
    await session.commit()
    return {"message": "전체 삭제 완료"}


@router.get("/status")
def status():
    """인덱서 상태 확인"""
    return {"status": "running"}
