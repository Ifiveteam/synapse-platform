"""Navigator 에이전트 스모크 — DB/HTTP 없이 실제 Gemini로 propose→compare→guide→chat 확인.

실행: cd backend && PYTHONPATH=. uv run python scripts/navigator_smoke.py
"""

import asyncio
import uuid

from app.core.env import load_backend_env

load_backend_env()

from langchain_core.messages import HumanMessage  # noqa: E402

from app.agents.navigator import get_navigator_agent  # noqa: E402
from app.agents.navigator.axes import extract_8axis  # noqa: E402
from app.agents.navigator.sub_agent.guide.store import CatalogHit  # noqa: E402


class FakeCatalogStore:
    """스모크용 가짜 store — 축별 캔드 시청 근거 반환."""

    async def search_by_axis(self, user_id, query_embedding, limit):
        return [
            CatalogHit(
                title="딥다이브: 경제 데이터 심층 분석",
                channel="테크리뷰",
                category_id="28",
                similarity=0.82,
            ),
            CatalogHit(
                title="초보를 위한 통계 해설",
                channel="데이터랩",
                category_id="27",
                similarity=0.74,
            ),
        ][:limit]


PROFILE_21 = {
    "self_direction": 75,
    "stimulation": 60,
    "achievement": 55,
    "power": 30,
    "security": 40,
    "benevolence": 65,
    "universalism": 70,
    "hedonism": 50,
    "conformity": 35,
    "tradition": 25,
    "novelty_seeking": 80,
    "persistence": 45,
    "self_transcendence": 60,
    "exploration": 85,
    "analytical": 35,
    "creativity": 70,
    "execution": 40,
    "achievement_drive": 50,
    "autonomy": 78,
    "sociality": 45,
    "sensitivity": 62,
}
TOP = {
    "categories": [{"category_id": "28", "count": 40}],
    "channels": [{"channel": "테크리뷰", "count": 30}],
}


async def main() -> None:
    agent = get_navigator_agent()

    print("\n===== ① propose (3종) =====")
    proposals = await agent.propose(PROFILE_21, TOP)
    for t, radar in proposals:
        print(f"[{t.value}] {radar.scores()}")
        print(f"   근거: {radar.reasoning[:80]}")

    chosen_type, chosen = proposals[0]
    ideal_8 = chosen.scores()

    print("\n===== ② compare (gap) =====")
    comp = agent.compare(PROFILE_21, ideal_8)
    print(f"total_gap={comp.total_gap}")
    for g in comp.gaps:
        print(f"   {g.label_ko}({g.axis}): {g.current}->{g.ideal} (gap {g.gap})")

    print("\n===== ③ guide (서브에이전트: RAG→생성→검증, 가짜 store) =====")
    guide = await agent.generate_guide(
        store=FakeCatalogStore(),
        user_id=uuid.uuid4(),
        profile_21=PROFILE_21,
        ideal_8=ideal_8,
        ideal_type=chosen_type.value,
        reasoning=chosen.reasoning,
    )
    print(f"요약: {guide.summary[:100]}")
    for s in guide.steps:
        print(f"   [{s.priority}] {s.label_ko}({s.axis}): {s.title}")

    print("\n===== ③-2 guide 폴백 (store=None → 일반 가이드) =====")
    guide_fb = await agent.generate_guide(
        store=None,
        user_id=uuid.uuid4(),
        profile_21=PROFILE_21,
        ideal_8=ideal_8,
        ideal_type=chosen_type.value,
        reasoning=chosen.reasoning,
    )
    print(f"요약: {guide_fb.summary[:80]} (steps {len(guide_fb.steps)})")

    print("\n===== ④ chat (interpret -> respond, SSE 이벤트) =====")
    async for ev in agent.chat_stream(
        messages=[HumanMessage(content="창의력을 좀 더 올리고 분석도 키우고 싶어")],
        user_id=uuid.uuid4(),
        session_id="smoke",
        profile_21=PROFILE_21,
        current_8axis=extract_8axis(PROFILE_21),
        working_ideal=ideal_8,
        ideal_type=chosen_type.value,
        top_interests=TOP,
    ):
        preview = ev.content[:50].replace("\n", " ")
        print(f"   <{ev.event}> {preview}")

    print("\n===== ✅ smoke done =====")


if __name__ == "__main__":
    asyncio.run(main())
