"""Navigator 서비스 — 프로필 로드·이상향 영속·SSE 오케스트레이션."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.navigator.base import NavigatorAgent, get_navigator_agent
from app.agents.navigator.constants import (
    BEHAVIOR_AXES,
    MAX_HISTORY_MESSAGES,
    STREAM_ERROR_PREFIX,
    TOP_INTERESTS_LIMIT,
    VALUES_TEMPERAMENT_AXES,
)
from app.agents.navigator.streaming import format_stream_event
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
    GuideResponse,
    IdealResponse,
    NavigatorChatRequest,
    ProposalItem,
    ProposalsResponse,
)
from app.services.profiler.scores import history_scores_dict

_PROFILE_404 = "Profile not found. Run POST /profiler/run first."
_IDEAL_404 = (
    "Ideal persona not found. Confirm an ideal via POST /navigator/ideal first."
)


def should_persist_assistant_log(content: str) -> bool:
    """빈 본문·엔진 오류(❌) 토큰은 DB에 남기지 않는다."""
    normalized = content.strip()
    return bool(normalized) and not normalized.startswith(STREAM_ERROR_PREFIX)


def _persona_scores(persona: UserIdealPersona) -> dict[str, float]:
    return {axis: float(getattr(persona, axis) or 0.0) for axis in BEHAVIOR_AXES}


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
        persona_label=persona.persona_label or "",
        reasoning=reasoning,
        is_active=persona.is_active,
        updated_at=persona.updated_at,
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
    ) -> tuple[dict[str, float], dict[str, float], dict[str, list], uuid.UUID]:
        if snapshot_id is not None:
            row = await fetch_profile_snapshot(self.db, user_id, snapshot_id)
        else:
            row = await fetch_latest_profile(self.db, user_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PROFILE_404
            )
        profile_21 = history_scores_dict(row)
        current_8axis = self.agent.current_axes(profile_21)
        top_interests = {
            "categories": await fetch_top_categories(
                self.db, user_id, limit=TOP_INTERESTS_LIMIT
            ),
            "channels": await fetch_top_channels(
                self.db, user_id, limit=TOP_INTERESTS_LIMIT
            ),
        }
        return profile_21, current_8axis, top_interests, row.id

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
        proposals = await self.agent.propose(profile_21, top_interests)
        items = [
            ProposalItem(
                ideal_type=p.ideal_type.value,
                scores=AxisScores8(**p.scores8),
                values_temperament=AxisScores13(**p.values13),
                persona_label=p.persona_label or self.agent.persona_label(p.scores8),
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
            _snap,
        ) = await self._load_profile_or_404(user_id)

        session_id = request.session_id or await self.repo.resolve_session_id(
            user_id=user_id
        )
        prior_history = await self.repo.get_chat_history(
            session_id=session_id, user_id=user_id
        )
        await self.repo.save_chat_log(
            session_id=session_id, user_id=user_id, role="user", content=request.message
        )

        messages = _history_to_messages(prior_history)
        messages.append(HumanMessage(content=request.message))

        # 이상향 시드(13축이 원본): 요청 값 우선, 없으면 저장된 활성 이상향
        ideal_type = request.ideal_type
        working_values: dict[str, float] | None = None
        if request.working_values is not None:
            working_values = request.working_values.model_dump()
        else:
            persona = await self.repo.get_active_ideal(user_id=user_id)
            if persona is not None:
                if persona.values_temperament:
                    working_values = dict(persona.values_temperament)
                if ideal_type is None:
                    ideal_type, _ = decode_description(persona.description)

        working_ideal = (
            self.agent.derive_behavior(working_values) if working_values else None
        )

        token_chunks: list[str] = []
        async for event in self.agent.chat_stream(
            messages=messages,
            user_id=user_id,
            session_id=session_id,
            profile_21=profile_21,
            current_8axis=current_8axis,
            working_ideal=working_ideal,
            working_values=working_values,
            ideal_type=ideal_type,
            top_interests=top_interests,
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
            scores8 = self.agent.derive_behavior(values13)
        else:
            values13 = None
            scores8 = self.agent.normalize_ideal(request.scores.model_dump())

        persona_label = request.persona_label or self.agent.persona_label(scores8)
        persona = await self.repo.create_ideal(
            user_id=user_id,
            scores8=scores8,
            ideal_type=request.ideal_type,
            reasoning=request.reasoning,
            persona_label=persona_label,
            values_temperament=values13,
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
        profile_21, current_8axis, _interests, _snap = await self._load_profile_or_404(
            user_id, persona.source_profile_history_id
        )
        ideal_8 = _persona_scores(persona)
        comparison = self.agent.compare(profile_21, ideal_8)
        # 13축: 현재=스냅샷에서 추출, 이상향=저장값(없으면 null)
        current_vt = _vt_or_none(
            {axis: profile_21.get(axis, 0.0) for axis in VALUES_TEMPERAMENT_AXES}
        )
        ideal_vt = _vt_or_none(persona.values_temperament)
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

        # 생성: 이상향이 만들어진 그 스냅샷(버전 고정) 기준으로 가이드를 만든다.
        profile_21, _current, _interests, _snap = await self._load_profile_or_404(
            user_id, persona.source_profile_history_id
        )
        ideal_8 = _persona_scores(persona)
        ideal_type, reasoning = decode_description(persona.description)
        guide = await self.agent.generate_guide(
            store=self.repo,
            user_id=user_id,
            profile_21=profile_21,
            ideal_8=ideal_8,
            ideal_type=ideal_type,
            reasoning=reasoning,
        )
        guide_json = {
            "summary": guide.summary,
            "steps": [
                {
                    "axis": s.axis,
                    "label_ko": s.label_ko,
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


def _history_to_messages(history: list) -> list[BaseMessage]:
    trimmed = history[-MAX_HISTORY_MESSAGES:] if MAX_HISTORY_MESSAGES > 0 else history
    messages: list[BaseMessage] = []
    for item in trimmed:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
    return messages
