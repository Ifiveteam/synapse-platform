"""Curator 툴 — LLM이 직접 호출하는 데이터 조회 함수들."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.curator.constants import (
    ANALYSIS_SEARCH_LIMIT,
    VIDEO_SEARCH_LIMIT,
)
from app.agents.shared.embedding import embed_texts

logger = logging.getLogger(__name__)

_CATEGORY_NAMES: dict[str, str] = {
    "1": "영화/애니메이션",
    "2": "자동차/교통",
    "10": "음악",
    "15": "반려동물",
    "17": "스포츠",
    "19": "여행/이벤트",
    "20": "게임",
    "22": "사람/블로그",
    "23": "코미디",
    "24": "엔터테인먼트",
    "25": "뉴스/정치",
    "26": "라이프스타일",
    "27": "교육",
    "28": "과학/기술",
    "29": "비영리/사회운동",
}

# query_db가 SELECT할 수 있는 테이블 전체 목록 (DB_SCHEMA와 반드시 동기화).
# LLM이 SQL을 직접 생성하다 보니 "user_subscriptions"처럼 없는 테이블명(복수형 등)을
# 지어내 raw DB 에러가 그대로 유저에게 노출되는 사고가 있었다 — 실행 전에 걸러낸다.
_KNOWN_TABLES = {
    "USER_WATCH_CATALOG",
    "USER_SUBSCRIPTION",
    "USER_PROFILE",
    "USER_PROFILE_HISTORY",
    "USER_IDEAL_PERSONA",
    "SCRAP",
}

# 조회 결과가 비었을 때, 테이블별로 "왜 없는지"를 구체적으로 알려주는 힌트.
# 이게 없으면 respond가 무관한 이전 답변(예: 시청 기록)을 끌어다 써서 엉뚱하게 답하기 쉽다.
_EMPTY_RESULT_HINTS: dict[str, str] = {
    "USER_SUBSCRIPTION": (
        "조회 결과가 없습니다. 구독 채널 정보는 YouTube Takeout 전체 ZIP 파일에만 들어있어서, "
        "시청 기록(watch-history) JSON/HTML만 업로드했다면 원래 비어 있는 게 정상입니다. "
        "구독 목록을 보려면 Takeout에서 전체 내보내기(ZIP)를 업로드해야 합니다."
    ),
    "USER_WATCH_CATALOG": (
        "조회 결과가 없습니다. 시청 기록은 유저당 최근 60일치만 보관됩니다. "
        "그보다 오래된 기간(예: 작년)을 물어봤다면 시스템에 원래 없는 게 정상이고, "
        "아직 분석 데이터를 업로드하지 않았어도 비어 있을 수 있습니다. "
        "'왜 없는지'를 유저에게 설명할 때 이 60일 보관 기준을 근거로 답하세요."
    ),
}

_CATEGORY_MAP_TEXT = ", ".join(f"{k}={v}" for k, v in _CATEGORY_NAMES.items())

# DB 스키마 — LLM이 SQL 생성 시 참고
DB_SCHEMA = """
## 조회 가능한 테이블 (모두 user_id로 필터링 필수)

⚠️ 컬럼명은 테이블마다 다릅니다 — 반드시 아래 스펠링 그대로 쓰세요.
채널명 컬럼: user_watch_catalog는 `channel`, user_subscription은 `channel_title`입니다.
(`channel_title`을 user_watch_catalog에, `channel_name`을 아무 테이블에나 쓰면 컬럼이 없어 조회가 실패합니다.)

⚠️ 두 테이블에는 공용 `channel_id` 같은 숫자/ID 조인 키가 없습니다. 시청 기록과 구독 채널을
JOIN해야 하면(예: "구독 채널 중 많이 본 것") 반드시 텍스트로 매칭하세요:
`user_watch_catalog.channel = user_subscription.channel_title`
(`ON ... channel_id = ... channel_id`처럼 존재하지 않는 컬럼으로 조인하지 마세요.)

### user_watch_catalog — 유튜브 시청 기록
- id (uuid)
- user_id (uuid)
- title (text) — 영상 제목
- channel (text) — 채널명
- watched_at (timestamptz) — 시청 시각
- is_shorts (bool) — 쇼츠 여부
- youtube_category_id (text) — 카테고리 ID. 매핑: __CATEGORY_MAP__
  ⚠️ 답변 어디에도 이 ID 숫자를 절대 언급하지 마세요. "22: 4486회", "20번 카테고리",
  "category 22"처럼 숫자를 노출하는 표현을 전부 금지합니다. 위 매핑으로 변환한
  이름만 쓰세요 (예: "사람/블로그: 4486회", "게임 카테고리"). 리스트든 문장 설명이든 예외 없습니다.
- url (text) — 영상 URL

예시: 특정 채널이 뭐하는 채널인지 파악 ("OO 채널 뭐야?" 질문용)
SELECT title, youtube_category_id FROM user_watch_catalog
WHERE user_id = '{user_id}' AND channel = '채널명' ORDER BY watched_at DESC LIMIT 10

### user_subscription — 구독 채널
- user_id (uuid)
- channel_title (text) — 채널명
- channel_url (text)

### user_profile — 최신 성향 분석
- user_id (uuid)
- persona_label (text) — 페르소나 이름
- summary_text (text) — 성향 요약
- dominant_traits (jsonb) — 주요 특성
- behavior_reasoning (text) — 행동 분석
- tone_of_user (text) — 성향 톤
- exploration, analytical, creativity, execution, achievement_drive, autonomy, sociality, sensitivity (float) — 8축 점수 (0~1)

### user_profile_history — 성향 변화 이력
- user_id (uuid)
- snapshot_date (date) — 분석 날짜
- persona_label (text)
- summary_text (text)
- exploration, analytical, creativity, execution, achievement_drive, autonomy, sociality, sensitivity (float)

### user_ideal_persona — 이상향 페르소나
- user_id (uuid)
- persona_label (text)
- description (text)
- is_active (bool)
- exploration, analytical, creativity, execution, achievement_drive, autonomy, sociality, sensitivity (float)

### scrap — 저장한 스크랩
- user_id (uuid)
- title (text)
- url (text)
- summary (text)
- category (text)
- tags (text[])
- created_at (timestamptz)
""".replace("__CATEGORY_MAP__", _CATEGORY_MAP_TEXT)


def _emit_chart(writer, chart_type: str, title: str, items: list) -> None:
    writer(
        {
            "event": "chart",
            "content": json.dumps(
                {"type": chart_type, "title": title, "items": items}, ensure_ascii=False
            ),
        }
    )


def build_tools(db: AsyncSession, user_id: uuid.UUID) -> list:
    """db·user_id를 클로저로 캡처한 툴 목록을 반환합니다."""

    # LLM이 한 턴에 툴을 여러 개 동시 호출하면(예: "지난주랑 이번주 비교해줘" → query_db 2회)
    # LangGraph ToolNode가 asyncio.gather로 병렬 실행한다. 그런데 모든 툴이 같은
    # AsyncSession(db)을 클로저로 공유해서, 두 코루틴이 동시에 execute/rollback을
    # 건드리면 SQLAlchemy가 IllegalStateChangeError를 던진다(세션은 동시 사용 불가).
    # 이 락으로 이번 요청 안에서의 DB 접근을 직렬화해 경쟁을 막는다.
    db_lock = asyncio.Lock()

    @tool
    async def query_db(sql: str) -> str:
        """유저 데이터를 SQL로 조회합니다. 시청 기록, 구독 채널, 성향, 이상향, 스크랩 등 단순 데이터 조회에 사용하세요.
        SELECT문만 허용됩니다. user_id는 자동으로 안전하게 주입됩니다.

        Args:
            sql: 실행할 SELECT SQL. user_id 자리에 {user_id} 플레이스홀더를 사용하세요.
                 예: SELECT title, watched_at FROM user_watch_catalog WHERE user_id = '{user_id}' ORDER BY watched_at DESC LIMIT 5
                 예: SELECT COUNT(*) FROM user_watch_catalog WHERE user_id = '{user_id}' AND watched_at >= date_trunc('month', now())
        """
        writer = get_stream_writer()
        writer({"event": "status", "content": "데이터를 조회하는 중..."})
        async with db_lock:
            try:
                from sqlalchemy import text

                # {user_id} 플레이스홀더를 실제 user_id로 교체 (SQL 인젝션 방지용 UUID 형식 검증)
                safe_uid = str(user_id)
                safe_sql = sql.replace("{user_id}", safe_uid).replace(
                    ":user_id", safe_uid
                )

                # SELECT만 허용
                clean = safe_sql.strip().upper()
                if not clean.startswith("SELECT"):
                    return "SELECT 쿼리만 허용됩니다."

                # 위험 키워드 차단
                blocked = [
                    "DROP",
                    "DELETE",
                    "UPDATE",
                    "INSERT",
                    "ALTER",
                    "TRUNCATE",
                    "CREATE",
                ]
                if any(re.search(rf"\b{kw}\b", clean) for kw in blocked):
                    return "허용되지 않는 쿼리입니다."

                # 존재하지 않는 테이블명 자동 교정 — LLM이 복수형(user_subscriptions 등)을
                # 지어내는 일이 실제로 반복 발생했다. agent가 에러를 보고 알아서 재시도할
                # 거라 기대했지만 실제로는 에러 문구를 유저에게 그대로 전달하며 되물어서
                # (재시도에 의존하지 않고) 여기서 결정적으로 고쳐서 바로 실행한다.
                referenced = set(
                    re.findall(r"(?:FROM|JOIN)\s+([A-Z_][A-Z0-9_]*)", clean)
                )
                unknown = referenced - _KNOWN_TABLES
                for bad_table in unknown:
                    corrected = next(
                        (
                            t
                            for t in _KNOWN_TABLES
                            if t == bad_table.rstrip("S") or t + "S" == bad_table
                        ),
                        None,
                    )
                    if corrected:
                        safe_sql = re.sub(
                            rf"\b{bad_table}\b",
                            corrected.lower(),
                            safe_sql,
                            flags=re.IGNORECASE,
                        )
                        clean = safe_sql.strip().upper()

                referenced = set(
                    re.findall(r"(?:FROM|JOIN)\s+([A-Z_][A-Z0-9_]*)", clean)
                )
                unknown = referenced - _KNOWN_TABLES
                if unknown:
                    if "VIDEO_ANALYSIS" in unknown:
                        return (
                            "video_analysis는 query_db로 조회할 수 없습니다. "
                            "영상 내용 요약이 필요하면 search_analysis 툴을 그 영상 제목으로 호출하세요."
                        )
                    return (
                        f"{', '.join(t.lower() for t in sorted(unknown))} 테이블은 존재하지 않습니다. "
                        f"사용 가능한 테이블: {', '.join(t.lower() for t in sorted(_KNOWN_TABLES))}. "
                        "이 문구를 유저에게 보여주지 말고, 올바른 테이블명으로 query_db를 다시 호출하세요."
                    )

                # user_id 조건 강제 확인 — GROUP BY/ORDER BY/LIMIT/HAVING보다 반드시 앞에 삽입해야
                # 한다 (끝에 그냥 붙이면 "... LIMIT 5 WHERE user_id = ..." 같은 문법 오류가 난다).
                if safe_uid not in safe_sql:
                    clause_positions = [
                        p
                        for p in (
                            clean.find(kw)
                            for kw in (" GROUP BY", " ORDER BY", " LIMIT", " HAVING")
                        )
                        if p != -1
                    ]
                    insert_at = (
                        min(clause_positions)
                        if clause_positions
                        else len(safe_sql.rstrip(";"))
                    )
                    condition = (
                        f"AND user_id = '{safe_uid}'"
                        if "WHERE" in clean[:insert_at]
                        else f"WHERE user_id = '{safe_uid}'"
                    )
                    safe_sql = (
                        safe_sql[:insert_at].rstrip()
                        + f" {condition} "
                        + safe_sql[insert_at:].lstrip()
                    )
                    clean = safe_sql.strip().upper()

                rows = (await db.execute(text(safe_sql))).fetchall()

                if not rows:
                    for table, hint in _EMPTY_RESULT_HINTS.items():
                        if table in clean:
                            return hint
                    return "조회 결과가 없습니다."

                keys = rows[0]._fields if hasattr(rows[0], "_fields") else []
                if keys:
                    lines = [", ".join(str(v) for v in row) for row in rows]
                    header = " | ".join(keys)
                    return f"{header}\n" + "\n".join(lines)
                return "\n".join(str(row) for row in rows)

            except Exception as e:
                logger.warning("query_db failed: %s", e)
                # 롤백 안 하면 세션 트랜잭션이 "aborted" 상태로 남아, 같은 턴의 재시도는
                # 물론 요청 끝의 대화 저장(INSERT)까지 전부 실패한다 (실제로 겪은 장애).
                await db.rollback()
                # 컬럼명을 "DB_SCHEMA 참고"라고만 말하면 LLM이 또 지어낸 컬럼명(channel_name,
                # play_time, video_title 등 실존하지 않는 이름)으로 재시도하는 게 실제로 반복
                # 관찰됐다. 스키마를 매번 다시 텍스트로 보여줘야 재시도가 정확해진다.
                return (
                    "조회 실패: 존재하지 않는 컬럼명을 사용했을 수 있습니다. "
                    "이 문구와 아래 스키마를 유저에게 보여주지 말고, 정확한 컬럼명으로 **지금 바로** "
                    "query_db를 다시 호출하세요. '다시 시도해볼까요?' 처럼 유저에게 되묻지 말고 "
                    "스스로 즉시 재시도하세요 — 어차피 재시도 여부는 유저가 아니라 당신이 판단할 일입니다. "
                    "다시 시도해도 계속 실패하면, 절대 채널명·숫자 등을 지어내서 답하지 말고 "
                    "'조회에 실패했다'고 사실대로 유저에게 답하세요.\n\n"
                    f"{DB_SCHEMA}"
                )

    # DB_SCHEMA(테이블·컬럼·카테고리 매핑)를 실패 시 힌트로만 보여주면, 첫 시도가 성공한
    # 턴에는 LLM이 스키마를 한 번도 못 보고 지어내거나(운 좋으면 자기 지식으로 맞히고) 답한다.
    # 매번 툴 설명 자체에 포함시켜 실패 여부와 무관하게 항상 보이게 한다.
    query_db.description = f"{query_db.description}\n\n{DB_SCHEMA}"

    @tool
    async def search_videos(query: str) -> str:
        """특정 주제·키워드로 내 시청 영상을 벡터 검색합니다. 특정 주제 영상을 찾을 때 사용하세요.

        Args:
            query: 검색할 주제나 키워드 (예: "게임", "AI 머신러닝", "요리 레시피")
        """
        writer = get_stream_writer()
        writer({"event": "status", "content": f"'{query}' 관련 영상을 검색하는 중..."})
        async with db_lock:
            try:
                from sqlalchemy import text

                vecs = embed_texts([query])
                if not vecs:
                    return "임베딩 생성에 실패했습니다."
                vec = vecs[0]

                rows = (
                    await db.execute(
                        text("""
                            SELECT title, channel, watched_at,
                                   1 - (embedding <=> CAST(:vec AS vector)) AS score
                            FROM user_watch_catalog
                            WHERE user_id = :uid AND embedding IS NOT NULL
                            ORDER BY embedding <=> CAST(:vec AS vector)
                            LIMIT :lim
                        """),
                        {
                            "vec": str(vec),
                            "uid": str(user_id),
                            "lim": VIDEO_SEARCH_LIMIT,
                        },
                    )
                ).fetchall()

                if not rows:
                    return f"'{query}' 관련 시청 영상이 없습니다."

                _emit_chart(
                    writer,
                    "video_list",
                    f"'{query}' 관련 시청 영상",
                    [{"title": r.title, "channel": r.channel} for r in rows],
                )
                return f"'{query}' 관련 시청 영상:\n" + "\n".join(
                    f"· {r.title} ({r.channel}) — {r.watched_at.strftime('%Y-%m-%d %H:%M') if r.watched_at else ''}"
                    for r in rows
                )
            except Exception as e:
                logger.warning("search_videos failed: %s", e)
                return "영상 검색에 실패했습니다."

    @tool
    async def search_analysis(query: str) -> str:
        """특정 주제·키워드로 시청 영상의 분석 내용을 벡터 검색합니다. 영상 내용·요약·분석이 필요할 때 사용하세요.

        Args:
            query: 검색할 주제나 키워드 (예: "게임 전략", "파이썬 튜토리얼")
        """
        writer = get_stream_writer()
        writer(
            {
                "event": "status",
                "content": f"'{query}' 관련 영상 분석을 검색하는 중...",
            }
        )
        async with db_lock:
            try:
                from sqlalchemy import text

                vecs = embed_texts([query])
                if not vecs:
                    return "임베딩 생성에 실패했습니다."
                vec = vecs[0]

                rows = (
                    await db.execute(
                        text("""
                            SELECT va.summary_kr,
                                   1 - (va.embedding <=> CAST(:vec AS vector)) AS score
                            FROM video_analysis va
                            JOIN user_watch_catalog uwc ON va.catalog_id = uwc.id
                            WHERE uwc.user_id = :uid AND va.embedding IS NOT NULL
                            ORDER BY va.embedding <=> CAST(:vec AS vector)
                            LIMIT :lim
                        """),
                        {
                            "vec": str(vec),
                            "uid": str(user_id),
                            "lim": ANALYSIS_SEARCH_LIMIT,
                        },
                    )
                ).fetchall()

                if not rows:
                    return f"'{query}' 관련 영상 분석이 없습니다."

                return f"'{query}' 관련 영상 분석:\n" + "\n".join(
                    f"· {r.summary_kr}" for r in rows
                )
            except Exception as e:
                logger.warning("search_analysis failed: %s", e)
                return "영상 분석 검색에 실패했습니다."

    @tool
    async def get_top_subscribed_channels(days: int | None = None) -> str:
        """구독한 채널 중에서 실제로 많이 시청한 채널 순위를 보여줍니다.
        '구독 채널 중 많이 본 거', '구독한 채널 순위', '구독 채널 중 자주 보는 거' 같은
        질문에 사용하세요. query_db로 직접 JOIN을 시도하지 말고 이 툴을 쓰세요.

        Args:
            days: 최근 며칠로 한정할지 (예: 7 = 최근 일주일). 생략하면 보관된 전체 기간(최근 60일).
        """
        writer = get_stream_writer()
        writer({"event": "status", "content": "구독 채널 시청 순위를 조회하는 중..."})
        async with db_lock:
            try:
                from sqlalchemy import text

                params: dict[str, object] = {"uid": str(user_id)}
                date_filter = ""
                if days:
                    date_filter = (
                        "AND w.watched_at >= now() - make_interval(days => :days)"
                    )
                    params["days"] = days

                rows = (
                    await db.execute(
                        text(f"""
                            SELECT s.channel_title, COUNT(*) AS watch_count
                            FROM user_watch_catalog w
                            JOIN user_subscription s ON w.channel = s.channel_title
                            WHERE w.user_id = :uid {date_filter}
                            GROUP BY s.channel_title
                            ORDER BY watch_count DESC
                            LIMIT 5
                        """),
                        params,
                    )
                ).fetchall()

                if not rows:
                    return (
                        "구독 채널 중 시청 기록이 있는 채널이 없습니다. "
                        "구독은 했지만 아직 그 채널 영상을 안 봤거나, 채널명 표기가 안 맞을 수 있습니다."
                    )

                return "구독 채널 중 많이 본 순위:\n" + "\n".join(
                    f"{i + 1}. {r.channel_title}: {r.watch_count}회"
                    for i, r in enumerate(rows)
                )
            except Exception as e:
                logger.warning("get_top_subscribed_channels failed: %s", e)
                await db.rollback()
                return "구독 채널 시청 순위 조회에 실패했습니다."

    @tool
    async def get_persona_radar() -> str:
        """현재 성향(8축)과 이상향 목표(8축)를 비교하는 레이더 차트를 보여줍니다. '성향 비교', '이상향과 차이', '갭' 관련 질문에 사용하세요."""
        writer = get_stream_writer()
        writer({"event": "status", "content": "성향 비교 차트를 생성하는 중..."})
        async with db_lock:
            try:
                from sqlalchemy import desc, select

                from app.models.user_ideal_persona import UserIdealPersona
                from app.models.user_profile_history import UserProfileHistory

                axes = [
                    ("탐색", "exploration"),
                    ("분석", "analytical"),
                    ("창의", "creativity"),
                    ("실행", "execution"),
                    ("성취", "achievement_drive"),
                    ("자율", "autonomy"),
                    ("사회성", "sociality"),
                    ("감수성", "sensitivity"),
                ]

                current_row = (
                    await db.execute(
                        select(UserProfileHistory)
                        .where(UserProfileHistory.user_id == user_id)
                        .order_by(desc(UserProfileHistory.snapshot_date))
                        .limit(1)
                    )
                ).scalar_one_or_none()

                ideal_row = (
                    await db.execute(
                        select(UserIdealPersona)
                        .where(
                            UserIdealPersona.user_id == user_id,
                            UserIdealPersona.is_active.is_(True),
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()

                if not current_row:
                    return "성향 분석 데이터가 없습니다."

                items = []
                for label, key in axes:
                    current_val = getattr(current_row, key)
                    ideal_val = getattr(ideal_row, key) if ideal_row else None
                    items.append(
                        {
                            "axis": label,
                            "current": round((current_val or 0) * 100),
                            "ideal": round((ideal_val or 0) * 100)
                            if ideal_val is not None
                            else None,
                        }
                    )

                chart_title = (
                    "현재 vs 이상향 성향 비교" if ideal_row else "현재 성향 8축"
                )
                writer(
                    {
                        "event": "chart",
                        "content": json.dumps(
                            {
                                "type": "persona_radar",
                                "title": chart_title,
                                "items": items,
                            },
                            ensure_ascii=False,
                        ),
                    }
                )

                summary_parts = []
                if ideal_row and ideal_row.persona_label:
                    summary_parts.append(f"이상향: {ideal_row.persona_label}")
                gaps = [
                    f"{label} +{round((getattr(ideal_row, key) or 0) * 100) - round((getattr(current_row, key) or 0) * 100)}p"
                    for label, key in axes
                    if ideal_row
                    and getattr(ideal_row, key) is not None
                    and getattr(current_row, key) is not None
                    and (getattr(ideal_row, key) - getattr(current_row, key)) > 0.05
                ]
                if gaps:
                    summary_parts.append(f"주요 성장 목표: {', '.join(gaps[:3])}")
                return (
                    " / ".join(summary_parts) if summary_parts else "차트를 확인하세요."
                )
            except Exception as e:
                logger.warning("get_persona_radar failed: %s", e)
                return "성향 비교 차트 생성에 실패했습니다."

    @tool
    async def create_playlist() -> str:
        """이상향 페르소나 기반으로 맞춤 재생목록을 생성합니다. '재생목록 만들어줘', '영상 추천 목록 만들어줘' 같은 요청에 사용하세요."""
        writer = get_stream_writer()
        writer(
            {
                "event": "status",
                "content": "재생목록을 생성하는 중... (시간이 걸릴 수 있어요)",
            }
        )
        async with db_lock:
            try:
                from sqlalchemy import select

                from app.agents.navigator.facade import get_navigator_agent
                from app.models.user_ideal_persona import UserIdealPersona
                from app.repositories.navigator_repository import NavigatorRepository
                from app.services.navigator.service import NavigatorService

                persona = (
                    await db.execute(
                        select(UserIdealPersona)
                        .where(
                            UserIdealPersona.user_id == user_id,
                            UserIdealPersona.is_active.is_(True),
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()

                if not persona:
                    return "이상향이 설정되지 않았습니다. 네비게이터에서 이상향을 먼저 설정해주세요."

                nav_service = NavigatorService.__new__(NavigatorService)
                nav_service.db = db
                nav_service.repo = NavigatorRepository(db)
                nav_service.agent = get_navigator_agent()

                result = await nav_service.create_playlist(
                    user_id=user_id, ideal_id=persona.id
                )
                return (
                    f"재생목록을 만들었어요!\n"
                    f"제목: **{result.title}**\n"
                    f"영상 {len(result.items)}개가 큐레이션됐습니다.\n"
                    f"[재생목록 보러가기](/me/playlists)"
                )
            except Exception as e:
                logger.warning("create_playlist failed: %s", e)
                return f"재생목록 생성에 실패했습니다: {e}"

    @tool
    async def save_scrap(url: str, title: str = "") -> str:
        """URL을 스크랩(북마크)으로 저장합니다. '이 링크 저장해줘', '북마크해줘' 같은 요청에 사용하세요.

        Args:
            url: 저장할 페이지 URL (필수)
            title: 페이지 제목 (선택, 없으면 URL로 대체)
        """
        writer = get_stream_writer()
        writer({"event": "status", "content": "스크랩을 저장하는 중..."})
        async with db_lock:
            try:
                from app.agents.archiver.scrap.classifier import classify_scrap_content
                from app.repositories.scrap_repository import ScrapRepository

                display_title = title or url
                user_content = f"제목: {display_title}\nURL: {url}"

                try:
                    classification = await classify_scrap_content(user_content)
                    summary = classification.summary
                    category = classification.category
                    tags = classification.tags
                except Exception:
                    summary = display_title
                    category = "기타"
                    tags = []

                scrap_repo = ScrapRepository(db)
                scrap = await scrap_repo.create_scrap(
                    user_id=user_id,
                    source_type="web",
                    url=url,
                    title=display_title or None,
                    summary=summary,
                    category=category,
                    tags=tags,
                )
                await db.commit()
                return f"스크랩 저장 완료!\n**{scrap.title or url}**\n카테고리: {scrap.category}"
            except Exception as e:
                logger.warning("save_scrap failed: %s", e)
                return "스크랩 저장에 실패했습니다."

    return [
        query_db,
        search_videos,
        search_analysis,
        get_top_subscribed_channels,
        get_persona_radar,
        create_playlist,
        save_scrap,
    ]
