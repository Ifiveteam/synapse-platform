"""Navigator 서비스 — 프로필 로드·이상향 영속·SSE 오케스트레이션."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.navigator.axes import (
    clamp_scores,
    compare,
    disposition_from_portrait,
    extract_8axis,
    interest_from_portrait,
)
from app.agents.navigator.behavior_map import derive_8_from_13
from app.agents.navigator.constants import (
    BEHAVIOR_AXES,
    DISPOSITION_AXES,
    DISPOSITION_LABELS_KO,
    INTEREST_DOMAINS,
    MAX_HISTORY_MESSAGES,
    STREAM_ERROR_PREFIX,
    TOP_INTERESTS_LIMIT,
    VALUES_TEMPERAMENT_AXES,
)
from app.agents.navigator.facade import NavigatorAgent, get_navigator_agent
from app.agents.navigator.schemas import Guide, PlaylistItem
from app.agents.navigator.streaming import format_sse_event, format_stream_event
from app.agents.shared.persona import persona_from_scores
from app.core.database.session import get_db
from app.models.user_ideal_persona import UserIdealPersona
from app.repositories.indexer_repository import (
    fetch_top_categories,
    fetch_top_channels,
)
from app.repositories.navigator_repository import (
    NavigatorRepository,
    decode_description,
)
from app.repositories.profiler_repository import (
    fetch_latest_profile,
    fetch_profile_snapshot,
)
from app.schemas.navigator import (
    AxisGapItem,
    AxisScores8,
    AxisScores13,
    ComparisonResponse,
    ConfirmIdealRequest,
    DispositionPair,
    DomainPair,
    GuideResponse,
    IdealResponse,
    NavigatorChatRequest,
    PlaylistItemResponse,
    PlaylistResponse,
    PlaylistSummary,
    ProposalItem,
    ProposalsResponse,
)
from app.services.profiler.scores import history_scores_dict

_PROFILE_404 = "Profile not found. Run POST /profiler/run first."
_IDEAL_404 = (
    "Ideal persona not found. Confirm an ideal via POST /navigator/ideal first."
)
_PLAYLIST_404 = "Playlist not found."


def should_persist_assistant_log(content: str) -> bool:
    """빈 본문·엔진 오류(❌) 토큰은 DB에 남기지 않는다."""
    normalized = content.strip()
    return bool(normalized) and not normalized.startswith(STREAM_ERROR_PREFIX)


def _persona_scores(persona: UserIdealPersona) -> dict[str, float]:
    return {axis: float(getattr(persona, axis) or 0.0) for axis in BEHAVIOR_AXES}


def _disposition_pairs(
    current: dict[str, float], target: dict[str, float]
) -> list[DispositionPair]:
    """성향 6축 현재→목표 쌍 (6축 전부, 값 없으면 0)."""
    return [
        DispositionPair(
            key=k,
            label_ko=DISPOSITION_LABELS_KO.get(k, k),
            current=round(float(current.get(k, 0.0)), 1),
            target=round(float(target.get(k, 0.0)), 1),
        )
        for k in DISPOSITION_AXES
    ]


def _domain_pairs(
    current: dict[str, float], target: dict[str, float]
) -> list[DomainPair]:
    """관심 도메인 9개 현재→목표 쌍 (목표 큰 순)."""
    pairs = [
        DomainPair(
            domain=d,
            current=round(float(current.get(d, 0.0)), 1),
            target=round(float(target.get(d, 0.0)), 1),
        )
        for d in INTEREST_DOMAINS
    ]
    pairs.sort(key=lambda p: p.target, reverse=True)
    return pairs


def _vt_or_none(values: dict | None) -> AxisScores13 | None:
    """13축 dict → AxisScores13 (누락 키는 0). 비어 있으면 None."""
    if not values:
        return None
    return AxisScores13(
        **{axis: float(values.get(axis, 0.0)) for axis in VALUES_TEMPERAMENT_AXES}
    )


def _ideal_to_response(persona: UserIdealPersona) -> IdealResponse:
    ideal_type, reasoning = decode_description(persona.description)
    return IdealResponse(
        id=str(persona.id),
        ideal_type=ideal_type,
        scores=AxisScores8(**_persona_scores(persona)),
        values_temperament=_vt_or_none(persona.values_temperament),
        target_disposition=persona.target_disposition or None,
        target_interest=persona.target_interest or None,
        persona_label=persona.persona_label or "",
        reasoning=reasoning,
        is_active=persona.is_active,
        updated_at=persona.updated_at,
    )


def _playlist_to_response(row) -> PlaylistResponse:
    items = [
        PlaylistItemResponse(
            **it,
            url=f"https://www.youtube.com/watch?v={it.get('video_id', '')}",
        )
        for it in (row.items_json or [])
    ]
    return PlaylistResponse(
        id=str(row.id),
        ideal_id=str(row.ideal_id),
        title=row.title or "",
        summary=row.summary or "",
        items=items,
        youtube_playlist_id=row.youtube_playlist_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _playlist_summary(row) -> PlaylistSummary:
    return PlaylistSummary(
        id=str(row.id),
        title=row.title or "",
        item_count=len(row.items_json or []),
        youtube_playlist_id=row.youtube_playlist_id,
        created_at=row.created_at,
    )


class NavigatorService:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        agent: NavigatorAgent = Depends(get_navigator_agent),
    ) -> None:
        self.db = db
        self.repo = NavigatorRepository(db)
        self.agent = agent

    async def _load_profile_or_404(
        self, user_id: uuid.UUID, snapshot_id: uuid.UUID | None = None
    ) -> tuple[
        dict[str, float], dict[str, float], dict[str, list], dict | None, uuid.UUID
    ]:
        if snapshot_id is not None:
            row = await fetch_profile_snapshot(self.db, user_id, snapshot_id)
        else:
            row = await fetch_latest_profile(self.db, user_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PROFILE_404
            )
        profile_21 = history_scores_dict(row)
        current_8axis = extract_8axis(profile_21)
        # portrait(성향 6축·관심 도메인)는 이상향 설계의 주 신호. 옛 스냅샷은 None.
        portrait = getattr(row, "portrait", None)
        top_interests = {
            "categories": await fetch_top_categories(
                self.db, user_id, limit=TOP_INTERESTS_LIMIT
            ),
            "channels": await fetch_top_channels(
                self.db, user_id, limit=TOP_INTERESTS_LIMIT
            ),
        }
        return profile_21, current_8axis, top_interests, portrait, row.id

    async def get_proposals(
        self,
        *,
        user_id: uuid.UUID,
        source_profile_history_id: uuid.UUID | None = None,
        refresh: bool = False,
    ) -> ProposalsResponse:
        (
            profile_21,
            _current,
            top_interests,
            portrait,
            snapshot_id,
        ) = await self._load_profile_or_404(user_id, source_profile_history_id)

        # 캐시 히트: 같은 (user, snapshot)이면 저장된 3안 그대로 (refresh 아니면)
        if not refresh:
            cached = await self.repo.get_proposal_cache(
                user_id=user_id, snapshot_id=snapshot_id
            )
            if cached is not None and cached.proposals_json:
                return ProposalsResponse(
                    proposals=[
                        ProposalItem.model_validate(p) for p in cached.proposals_json
                    ]
                )

        # 생성 → 캐시 저장 → 반환
        proposals = await self.agent.propose(profile_21, portrait, top_interests)
        cur_disp = disposition_from_portrait(portrait)
        cur_interest = interest_from_portrait(portrait)
        items = [
            ProposalItem(
                ideal_type=p.ideal_type.value,
                scores=AxisScores8(**p.scores8),
                values_temperament=AxisScores13(**p.values13),
                disposition=_disposition_pairs(cur_disp, p.target_disposition),
                interest=_domain_pairs(cur_interest, p.target_interest),
                persona_label=p.persona_label
                or persona_from_scores(p.values13, p.scores8),
                reasoning=p.reasoning,
            )
            for p in proposals
        ]
        catalog_count = await self.repo.count_catalog(user_id=user_id)
        await self.repo.save_proposal_cache(
            user_id=user_id,
            snapshot_id=snapshot_id,
            proposals_json=[item.model_dump() for item in items],
            catalog_count=catalog_count,
        )
        return ProposalsResponse(proposals=items)

    async def stream_chat(
        self, request: NavigatorChatRequest, *, user_id: uuid.UUID
    ) -> AsyncIterator[str]:
        (
            profile_21,
            current_8axis,
            top_interests,
            portrait,
            _snap,
        ) = await self._load_profile_or_404(user_id)

        session_id = request.session_id or await self.repo.resolve_session_id(
            user_id=user_id
        )
        prior_history = await self.repo.get_chat_history(
            session_id=session_id, user_id=user_id
        )
        # 턴 = 이번 발화를 포함한 사용자 발화 수 (인터뷰 캡 판정용)
        turn = sum(1 for h in prior_history if h.role == "user") + 1

        messages = _history_to_messages(prior_history)
        if request.message.strip():
            await self.repo.save_chat_log(
                session_id=session_id,
                user_id=user_id,
                role="user",
                content=request.message,
            )
            messages.append(HumanMessage(content=request.message))

        # 이상향 시드: 요청 값 우선, 없으면 저장된 활성 이상향
        ideal_type = request.ideal_type
        working_values: dict[str, float] | None = None
        working_disposition: dict[str, float] | None = request.working_disposition
        working_interest: dict[str, float] | None = request.working_interest
        if request.working_values is not None:
            working_values = request.working_values.model_dump()
        else:
            persona = await self.repo.get_active_ideal(user_id=user_id)
            if persona is not None:
                if persona.values_temperament:
                    working_values = dict(persona.values_temperament)
                if working_disposition is None and persona.target_disposition:
                    working_disposition = dict(persona.target_disposition)
                if working_interest is None and persona.target_interest:
                    working_interest = dict(persona.target_interest)
                if ideal_type is None:
                    ideal_type, _ = decode_description(persona.description)

        working_ideal = derive_8_from_13(working_values) if working_values else None

        token_chunks: list[str] = []
        async for event in self.agent.chat_stream(
            messages=messages,
            user_id=user_id,
            session_id=session_id,
            profile_21=profile_21,
            current_8axis=current_8axis,
            portrait=portrait,
            working_ideal=working_ideal,
            working_values=working_values,
            working_disposition=working_disposition,
            working_interest=working_interest,
            ideal_type=ideal_type,
            top_interests=top_interests,
            turn=turn,
            force_finalize=request.force_finalize,
        ):
            yield format_stream_event(event)
            if event.event == "token":
                token_chunks.append(event.content)

        full_reply = "".join(token_chunks)
        if should_persist_assistant_log(full_reply):
            await self.repo.save_chat_log(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=full_reply,
            )

    async def confirm_ideal(
        self, request: ConfirmIdealRequest, *, user_id: uuid.UUID
    ) -> IdealResponse:
        """이상향을 새로 생성(보관). 적용은 apply로 별도."""
        snapshot_id: uuid.UUID | None = None
        if request.source_profile_history_id:
            try:
                snapshot_id = uuid.UUID(request.source_profile_history_id)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid source_profile_history_id",
                ) from exc
            row = await fetch_profile_snapshot(self.db, user_id, snapshot_id)
        else:
            row = await fetch_latest_profile(self.db, user_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PROFILE_404
            )

        # 13축이 오면 그게 설계 원본 → 8축은 거기서 파생(일관성 보장). 없으면 보낸 8축 사용.
        if request.values_temperament is not None:
            values13 = request.values_temperament.model_dump()
            scores8 = derive_8_from_13(values13)
        else:
            values13 = None
            scores8 = clamp_scores(request.scores.model_dump())

        persona_label = request.persona_label or persona_from_scores(
            values13 or {}, scores8
        )
        persona = await self.repo.create_ideal(
            user_id=user_id,
            scores8=scores8,
            ideal_type=request.ideal_type,
            reasoning=request.reasoning,
            persona_label=persona_label,
            values_temperament=values13,
            target_disposition=request.target_disposition,
            target_interest=request.target_interest,
            source_profile_history_id=row.id,
        )
        return _ideal_to_response(persona)

    async def list_ideals(self, *, user_id: uuid.UUID) -> list[IdealResponse]:
        personas = await self.repo.list_ideals(user_id=user_id)
        return [_ideal_to_response(p) for p in personas]

    async def get_ideal(
        self, *, user_id: uuid.UUID, ideal_id: uuid.UUID
    ) -> IdealResponse:
        persona = await self.repo.get_ideal(user_id=user_id, ideal_id=ideal_id)
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_IDEAL_404
            )
        return _ideal_to_response(persona)

    async def apply_ideal(
        self, *, user_id: uuid.UUID, ideal_id: uuid.UUID
    ) -> IdealResponse:
        persona = await self.repo.set_active(user_id=user_id, ideal_id=ideal_id)
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_IDEAL_404
            )
        return _ideal_to_response(persona)

    async def _ideal_or_404(
        self, user_id: uuid.UUID, ideal_id: uuid.UUID
    ) -> UserIdealPersona:
        persona = await self.repo.get_ideal(user_id=user_id, ideal_id=ideal_id)
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_IDEAL_404
            )
        return persona

    async def get_comparison(
        self, *, user_id: uuid.UUID, ideal_id: uuid.UUID
    ) -> ComparisonResponse:
        # 비교 기준 = 이상향이 만들어진 그 스냅샷(버전 고정). 없으면 최신.
        persona = await self._ideal_or_404(user_id, ideal_id)
        (
            profile_21,
            current_8axis,
            _interests,
            portrait,
            _snap,
        ) = await self._load_profile_or_404(user_id, persona.source_profile_history_id)
        ideal_8 = _persona_scores(persona)
        comparison = compare(current_8axis, ideal_8)
        # 13축: 현재=스냅샷에서 추출, 이상향=저장값(없으면 null)
        current_vt = _vt_or_none(
            {axis: profile_21.get(axis, 0.0) for axis in VALUES_TEMPERAMENT_AXES}
        )
        ideal_vt = _vt_or_none(persona.values_temperament)
        # 주 표시 축: 성향·도메인 현재(스냅샷 초상)→목표(저장값)
        disposition = _disposition_pairs(
            disposition_from_portrait(portrait), persona.target_disposition or {}
        )
        interest = _domain_pairs(
            interest_from_portrait(portrait), persona.target_interest or {}
        )
        return ComparisonResponse(
            current=AxisScores8(**current_8axis),
            ideal=AxisScores8(**ideal_8),
            gaps=[
                AxisGapItem(
                    axis=g.axis,
                    label_ko=g.label_ko,
                    current=g.current,
                    ideal=g.ideal,
                    gap=g.gap,
                )
                for g in comparison.gaps
            ],
            total_gap=comparison.total_gap,
            current_vt=current_vt,
            ideal_vt=ideal_vt,
            disposition=disposition,
            interest=interest,
        )

    async def get_guide(
        self, *, user_id: uuid.UUID, ideal_id: uuid.UUID, refresh: bool = False
    ) -> GuideResponse:
        persona = await self._ideal_or_404(user_id, ideal_id)
        catalog_count = await self.repo.count_catalog(user_id=user_id)

        # 캐시 히트: 저장된 가이드가 있고 강제 재생성이 아니면 그대로 반환.
        # 생성 당시보다 시청기록이 늘었으면 stale=True 로 재생성을 권한다.
        if persona.guide_json and not refresh:
            stale = persona.guide_catalog_count != catalog_count
            return GuideResponse(
                **persona.guide_json,
                generated_at=persona.guide_generated_at,
                stale=stale,
            )

        # 생성: 이상향이 만들어진 그 스냅샷(버전 고정) 기준. 목표 없으면(레거시) 안내.
        ideal_type, reasoning = decode_description(persona.description)
        if not persona.target_disposition and not persona.target_interest:
            guide = Guide(
                summary=(
                    "이 이상향에는 성향·도메인 목표가 없어(예전 버전) 맞춤 가이드를 "
                    "만들 수 없어요. 이상향을 새로 만들면 제공됩니다."
                ),
                steps=[],
            )
        else:
            (
                _p21,
                _current,
                _interests,
                portrait,
                _snap,
            ) = await self._load_profile_or_404(
                user_id, persona.source_profile_history_id
            )
            guide = await self.agent.generate_guide(
                store=self.repo,
                user_id=user_id,
                current_disposition=disposition_from_portrait(portrait),
                current_interest=interest_from_portrait(portrait),
                target_disposition=dict(persona.target_disposition or {}),
                target_interest=dict(persona.target_interest or {}),
                ideal_type=ideal_type,
                reasoning=reasoning,
            )
        guide_json = {
            "summary": guide.summary,
            "steps": [
                {
                    "axis": s.axis,
                    "label_ko": s.label_ko,
                    "kind": s.kind,
                    "title": s.title,
                    "detail": s.detail,
                    "priority": s.priority,
                }
                for s in guide.steps
            ],
        }
        saved = await self.repo.save_guide(
            user_id=user_id,
            ideal_id=ideal_id,
            guide_json=guide_json,
            catalog_count=catalog_count,
        )
        return GuideResponse(
            **guide_json,
            generated_at=saved.guide_generated_at if saved else None,
            stale=False,
        )

    # ── 재생목록 (navigator_playlist, 이상향 1개 : N개) ──────────────
    async def create_playlist(
        self, *, user_id: uuid.UUID, ideal_id: uuid.UUID
    ) -> PlaylistResponse:
        """이상향 페르소나+시청기록 근거로 새 재생목록을 생성·저장한다."""
        persona = await self._ideal_or_404(user_id, ideal_id)
        persona_label = persona.persona_label or "추천 재생목록"
        values13 = persona.values_temperament or {}
        ideal_type, reasoning = decode_description(persona.description)

        build = await self.agent.generate_playlist(
            store=self.repo,
            user_id=user_id,
            persona_label=persona_label,
            values13=values13,
            ideal_type=ideal_type,
            reasoning=reasoning,
        )

        existing = await self.repo.list_playlists(user_id=user_id, ideal_id=ideal_id)
        title = f"{persona_label} #{len(existing) + 1}"
        row = await self.repo.create_playlist(
            user_id=user_id,
            ideal_id=ideal_id,
            title=title,
            summary=build.playlist.summary,
            items_json=[it.model_dump() for it in build.playlist.items],
            channels_json=[
                {"channel_id": c.channel_id, "title": c.title} for c in build.channels
            ],
            reservoir_json=[it.model_dump() for it in build.reservoir],
        )
        return _playlist_to_response(row)

    async def list_playlists(
        self, *, user_id: uuid.UUID, ideal_id: uuid.UUID
    ) -> list[PlaylistSummary]:
        await self._ideal_or_404(user_id, ideal_id)
        rows = await self.repo.list_playlists(user_id=user_id, ideal_id=ideal_id)
        return [_playlist_summary(r) for r in rows]

    async def get_playlist(
        self, *, user_id: uuid.UUID, playlist_id: uuid.UUID
    ) -> PlaylistResponse:
        row = await self.repo.get_playlist(user_id=user_id, playlist_id=playlist_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PLAYLIST_404
            )
        return _playlist_to_response(row)

    async def rename_playlist(
        self, *, user_id: uuid.UUID, playlist_id: uuid.UUID, title: str
    ) -> PlaylistResponse:
        row = await self.repo.rename_playlist(
            user_id=user_id, playlist_id=playlist_id, title=title
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PLAYLIST_404
            )
        return _playlist_to_response(row)

    async def delete_playlist(
        self, *, user_id: uuid.UUID, playlist_id: uuid.UUID
    ) -> None:
        ok = await self.repo.delete_playlist(user_id=user_id, playlist_id=playlist_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PLAYLIST_404
            )

    async def refresh_item(
        self, *, user_id: uuid.UUID, playlist_id: uuid.UUID, video_id: str
    ) -> PlaylistResponse:
        """재생목록 영상 1개를 새 후보로 교체 (저수지→채널 re-RSS)."""
        row = await self.repo.get_playlist(user_id=user_id, playlist_id=playlist_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PLAYLIST_404
            )
        items = [PlaylistItem(**it) for it in (row.items_json or [])]
        reservoir = [PlaylistItem(**it) for it in (row.reservoir_json or [])]
        channel_ids = [
            c["channel_id"] for c in (row.channels_json or []) if c.get("channel_id")
        ]
        result = await self.agent.refresh_item(
            store=self.repo,
            user_id=user_id,
            items=items,
            reservoir=reservoir,
            channel_ids=channel_ids,
            target_video_id=video_id,
        )
        if result.new_item is None:
            return _playlist_to_response(row)  # 교체 후보 없음 → 현재 유지
        saved = await self.repo.update_playlist(
            user_id=user_id,
            playlist_id=playlist_id,
            items_json=[i.model_dump() for i in result.items],
            reservoir_json=[i.model_dump() for i in result.reservoir],
        )
        return _playlist_to_response(saved or row)

    async def regenerate_playlist(
        self, *, user_id: uuid.UUID, playlist_id: uuid.UUID
    ) -> PlaylistResponse:
        """재생목록을 통째로 재생성(채널 재발굴→큐레이션) 후 같은 행에 갱신."""
        row = await self.repo.get_playlist(user_id=user_id, playlist_id=playlist_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PLAYLIST_404
            )
        persona = await self._ideal_or_404(user_id, row.ideal_id)
        persona_label = persona.persona_label or "추천 재생목록"
        values13 = persona.values_temperament or {}
        ideal_type, reasoning = decode_description(persona.description)

        build = await self.agent.generate_playlist(
            store=self.repo,
            user_id=user_id,
            persona_label=persona_label,
            values13=values13,
            ideal_type=ideal_type,
            reasoning=reasoning,
        )
        # 재생성 결과가 비면 기존 재생목록을 덮어쓰지 않는다 (날아가는 것 방지)
        if not build.playlist.items:
            return _playlist_to_response(row)
        saved = await self.repo.update_playlist(
            user_id=user_id,
            playlist_id=playlist_id,
            items_json=[it.model_dump() for it in build.playlist.items],
            channels_json=[
                {"channel_id": c.channel_id, "title": c.title} for c in build.channels
            ],
            reservoir_json=[it.model_dump() for it in build.reservoir],
            summary=build.playlist.summary,
        )
        return _playlist_to_response(saved or row)

    async def chat_edit(
        self, *, user_id: uuid.UUID, playlist_id: uuid.UUID, message: str
    ) -> AsyncIterator[str]:
        """채팅으로 재생목록 부분수정 (SSE: status 진행 + 최종 playlist 갱신)."""
        row = await self.repo.get_playlist(user_id=user_id, playlist_id=playlist_id)
        if row is None:
            yield format_sse_event(
                event="status", content="재생목록을 찾을 수 없습니다."
            )
            return

        items = [PlaylistItem(**it) for it in (row.items_json or [])]
        reservoir = [PlaylistItem(**it) for it in (row.reservoir_json or [])]
        channels = list(row.channels_json or [])

        final_payload: dict | None = None
        async for ev in self.agent.edit_playlist(
            store=self.repo,
            user_id=user_id,
            items=items,
            reservoir=reservoir,
            channels=channels,
            message=message,
        ):
            if ev.event == "playlist":
                final_payload = json.loads(ev.content)
                continue
            yield format_stream_event(ev)

        if final_payload is not None:
            saved = await self.repo.update_playlist(
                user_id=user_id,
                playlist_id=playlist_id,
                items_json=final_payload["items"],
                reservoir_json=final_payload["reservoir"],
                channels_json=final_payload["channels"],
            )
            resp = _playlist_to_response(saved or row)
            yield format_sse_event(event="playlist", content=resp.model_dump_json())


def _history_to_messages(history: list) -> list[BaseMessage]:
    trimmed = history[-MAX_HISTORY_MESSAGES:] if MAX_HISTORY_MESSAGES > 0 else history
    messages: list[BaseMessage] = []
    for item in trimmed:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
    return messages
