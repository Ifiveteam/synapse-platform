"""Navigator 에이전트 스모크 — DB/HTTP 없이 실제 Gemini로 propose→compare→guide→chat 확인.

목적: 특히 propose 3안(반대/심화/균형)이 성향·도메인에서 **뚜렷이 갈라지는지** 눈으로 확인.
실행: cd backend && PYTHONPATH=. uv run python scripts/navigator_smoke.py
"""

import asyncio
import uuid

from app.core.env import load_backend_env

load_backend_env()

from langchain_core.messages import HumanMessage  # noqa: E402

from app.agents.navigator import get_navigator_agent  # noqa: E402
from app.agents.navigator.axes import compare, extract_8axis  # noqa: E402
from app.agents.navigator.constants import (  # noqa: E402
    DISPOSITION_AXES,
    DISPOSITION_LABELS_KO,
    INTEREST_DOMAINS,
)
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

# 게임·스포츠에 편중, 몰입·팬심 높고 탐험·정보 낮은 초상 (반대형이 극단으로 갈려야 함)
PORTRAIT = {
    "persona_label": "열정적인 멀티 팬 탐험가",
    "keywords": ["게임", "축구", "숏폼", "즉흥적", "하이라이트"],
    "interest": [
        {"axis": "게임", "value": 42.0},
        {"axis": "스포츠", "value": 30.0},
        {"axis": "예능", "value": 14.0},
        {"axis": "음악", "value": 8.0},
        {"axis": "인물·일상", "value": 3.0},
        {"axis": "라이프·취미", "value": 2.0},
        {"axis": "영화·애니", "value": 1.0},
        {"axis": "뉴스·시사", "value": 0.0},
        {"axis": "지식·교육", "value": 0.0},
    ],
    "disposition": [
        {"axis": "몰입도", "value": 72},
        {"axis": "탐험성", "value": 28},
        {"axis": "팬심", "value": 80},
        {"axis": "트렌드민감", "value": 66},
        {"axis": "정보추구", "value": 18},
        {"axis": "감성지향", "value": 44},
    ],
    "style": [],
    "reasoning": "게임·스포츠 하이라이트를 즉흥적으로 몰아보는 팬 성향.",
}
TOP = {
    "categories": [{"category_id": "20", "count": 42}],
    "channels": [{"channel": "게임채널", "count": 30}],
}


def _fmt_disp(d: dict[str, float]) -> str:
    return "  ".join(
        f"{DISPOSITION_LABELS_KO[a]}:{round(d.get(a, 0.0))}" for a in DISPOSITION_AXES
    )


def _fmt_interest(d: dict[str, float]) -> str:
    top = sorted(INTEREST_DOMAINS, key=lambda x: d.get(x, 0.0), reverse=True)[:4]
    return "  ".join(f"{x}:{round(d.get(x, 0.0))}" for x in top)


async def main() -> None:
    agent = get_navigator_agent()

    print("\n===== ① propose (3종) — 성향·도메인 목표 =====")
    proposals = await agent.propose(PROFILE_21, PORTRAIT, TOP)
    for p in proposals:
        print(f"\n[{p.ideal_type.value}] {p.persona_label}")
        print(f"   성향목표: {_fmt_disp(p.target_disposition)}")
        print(f"   도메인목표(top4): {_fmt_interest(p.target_interest)}")
        print(f"   근거: {p.reasoning[:90]}")

    chosen = proposals[0]
    ideal_8 = chosen.scores8

    print("\n===== ② compare (8축 gap, 내부) =====")
    comp = compare(extract_8axis(PROFILE_21), ideal_8)
    print(f"total_gap={comp.total_gap}")

    print("\n===== ③ guide (심화·확장, 가짜 store) =====")
    from app.agents.navigator.axes import (
        disposition_from_portrait,
        interest_from_portrait,
    )

    guide = await agent.generate_guide(
        store=FakeCatalogStore(),
        user_id=uuid.uuid4(),
        current_disposition=disposition_from_portrait(PORTRAIT),
        current_interest=interest_from_portrait(PORTRAIT),
        target_disposition=chosen.target_disposition,
        target_interest=chosen.target_interest,
        ideal_type=chosen.ideal_type.value,
        reasoning=chosen.reasoning,
    )
    print(f"요약: {guide.summary[:100]}")
    for s in guide.steps:
        print(f"   [{s.kind}] {s.label_ko}({s.axis}): {s.title}")

    print("\n===== ④ chat (interpret -> respond, SSE 이벤트) =====")
    async for ev in agent.chat_stream(
        messages=[HumanMessage(content="창의력을 좀 더 올리고 분석도 키우고 싶어")],
        user_id=uuid.uuid4(),
        session_id="smoke",
        profile_21=PROFILE_21,
        current_8axis=extract_8axis(PROFILE_21),
        working_ideal=ideal_8,
        ideal_type=chosen.ideal_type.value,
        top_interests=TOP,
    ):
        preview = ev.content[:50].replace("\n", " ")
        print(f"   <{ev.event}> {preview}")

    print("\n===== ✅ smoke done =====")


if __name__ == "__main__":
    asyncio.run(main())
