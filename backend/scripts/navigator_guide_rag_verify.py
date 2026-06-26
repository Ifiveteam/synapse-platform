"""Navigator 가이드 RAG 그라운딩 실검증.

실 DB(pgvector) + 실 임베딩(OpenAI)으로 user_watch_catalog에 시청 영상을 심고,
① repo.search_by_axis 가 약한 축 쿼리에 맞는 실제 영상을 cosine 으로 정확히 찾는지
② generate_guide(store=repo) 가 그 영상을 '근거로 무는'(grounded) 가이드를 만드는지
확인한다. 끝나면 심은 데이터(임시 유저 cascade)를 모두 정리한다.

실행: cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_guide_rag_verify.py
"""

import asyncio
import uuid
from datetime import datetime, timezone

from app.core.env import load_backend_env

load_backend_env()

from sqlalchemy import delete  # noqa: E402

from app.agents.navigator import get_navigator_agent  # noqa: E402
from app.agents.navigator.sub_agent.guide.constants import axis_query  # noqa: E402
from app.agents.shared.embedding import embed_texts  # noqa: E402
from app.core.database.session import AsyncSessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.user_watch_catalog import UserWatchCatalog  # noqa: E402
from app.repositories.navigator_repository import NavigatorRepository  # noqa: E402

# 현재 8축: analytical(분석)을 매우 낮게 → 이상향에서 크게 올려 약한 축 1순위로.
PROFILE_21 = {
    "self_direction": 70,
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
    # 행동 8축
    "exploration": 75,
    "analytical": 15,
    "creativity": 65,
    "execution": 30,
    "achievement_drive": 35,
    "autonomy": 72,
    "sociality": 55,
    "sensitivity": 60,
}

# 이상향 8축: analytical/execution/achievement_drive 를 크게 올림 → 약한 축 top3.
IDEAL_8 = {
    "exploration": 75,
    "analytical": 90,
    "creativity": 65,
    "execution": 80,
    "achievement_drive": 78,
    "autonomy": 72,
    "sociality": 55,
    "sensitivity": 60,
}

# 시청 영상 시드 — analytical 강하게 테마, + execution/achievement, + 무관 노이즈.
ANALYTICAL_CHANNELS = {"데이터랩", "씽크탱크", "분석왕"}
SEED_VIDEOS = [
    ("데이터 분석 마스터클래스: 통계로 세상 읽기", "데이터랩", "27"),
    ("비판적 사고력: 논리적으로 뉴스 해부하기", "씽크탱크", "27"),
    ("심층 리뷰 — 경제 지표를 데이터로 분석", "분석왕", "25"),
    ("따라하면 되는 파이썬 실전 튜토리얼", "코딩핸즈", "28"),
    ("아침 루틴으로 생산성 200% 끌어올리기", "갓생연구소", "26"),
    ("브이로그: 제주도 감성 여행 기록", "여행카페", "19"),
    ("ASMR 빗소리 3시간 수면용", "힐링사운드", "10"),
]


async def main() -> None:
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    print("===== 임베딩 생성 (OpenAI) =====")
    texts = [f"{title} - {ch}" for title, ch, _ in SEED_VIDEOS]
    vectors = await asyncio.to_thread(embed_texts, texts)
    print(f"  시드 {len(vectors)}건 임베딩 완료 (dim={len(vectors[0])})")

    async with AsyncSessionLocal() as session:
        try:
            session.add(
                User(
                    id=user_id,
                    email=f"ragverify+{user_id.hex[:8]}@synapse.test",
                    google_sub_id=f"ragverify-{user_id.hex[:8]}",
                    name="RAG Verify",
                )
            )
            for (title, ch, cat), vec in zip(SEED_VIDEOS, vectors, strict=True):
                session.add(
                    UserWatchCatalog(
                        user_id=user_id,
                        platform="youtube",
                        title=title,
                        url=f"https://youtu.be/{uuid.uuid4().hex[:11]}",
                        channel=ch,
                        watched_at=now,
                        youtube_category_id=cat,
                        embedding_text=f"{title} - {ch}",
                        embedding=vec,
                    )
                )
            await session.commit()
            print(
                f"  임시 유저 + 시청 {len(SEED_VIDEOS)}건 시드 완료 (user_id={user_id})"
            )

            repo = NavigatorRepository(session)

            # ── ① 직접 RAG 검색: analytical 쿼리 → 분석 테마 영상이 상위인가 ──
            print("\n===== ① repo.search_by_axis(analytical) =====")
            q_vec = (
                await asyncio.to_thread(embed_texts, [axis_query("analytical", 0)])
            )[0]
            hits = await repo.search_by_axis(user_id, q_vec, 5)
            for h in hits:
                mark = "✅분석" if h.channel in ANALYTICAL_CHANNELS else "  노이즈"
                print(f"  {mark}  sim={h.similarity:<7} {h.title} · {h.channel}")
            top_ok = bool(hits) and hits[0].channel in ANALYTICAL_CHANNELS
            print(f"  → 상위 1건이 분석 테마인가: {'✅ YES' if top_ok else '❌ NO'}")

            # ── ② end-to-end: generate_guide(store=repo) 가 근거를 무는가 ──
            print("\n===== ② generate_guide(store=repo) =====")
            agent = get_navigator_agent()
            guide = await agent.generate_guide(
                store=repo,
                user_id=user_id,
                profile_21=PROFILE_21,
                ideal_8=IDEAL_8,
                ideal_type="BALANCE",
                reasoning="분석·실행·성취 동기를 키워 균형을 맞춘다",
            )
            print(f"  요약: {guide.summary}")
            for s in guide.steps:
                print(f"   [{s.priority}] {s.label_ko}({s.axis}): {s.title}")
                print(f"        {s.detail}")

            blob = guide.summary + " ".join(
                f"{s.title} {s.detail}" for s in guide.steps
            )
            cited = sorted(
                {t for t, _, _ in SEED_VIDEOS if t in blob}
                | {c for _, c, _ in SEED_VIDEOS if c in blob}
            )
            print(f"\n  → 가이드가 언급한 실제 시청 영상/채널: {cited or '(없음)'}")
            grounded = bool(cited)
            print(
                f"  → 실시청 근거 그라운딩: {'✅ YES' if grounded else '⚠️  텍스트엔 미언급'}"
            )

            print("\n===== 판정 =====")
            print(f"  RAG 검색 정확도(①): {'PASS' if top_ok else 'FAIL'}")
            print(
                f"  그라운딩 가이드(②): {'PASS' if grounded else 'WEAK(근거검색은 됐으나 LLM이 영상명 미인용)'}"
            )
        finally:
            # 정리: 임시 유저 삭제 → catalog cascade
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
            print(f"\n🧹 cleanup: 임시 유저/시청 데이터 삭제 (user_id={user_id})")


if __name__ == "__main__":
    asyncio.run(main())
