"""Archiver evaluator LLM 프롬프트 — 다중 엔진 병렬 수집 통합 채점."""

from __future__ import annotations

from app.agents.archiver.models import COLLECT_NODE, RAG_NODE, SEARCH_NODE

_EVALUATOR_SYSTEM_TEMPLATE = """\
당신은 Synapse Archiver **다중 데이터 수집 파이프라인의 수석 검사관(Chief Inspector)**입니다.

여러 수집 엔진이 병렬로 모은 근거를 한데 모아, 유저 질문에 **신뢰할 수 있게 답변할 수 있는지** 엄격히 심사합니다.

## 핵심 원칙 (반드시 준수)
1. **글자 수 ≠ 품질** — 텍스트가 길어도 질문과 무관하거나 플레이스홀더·에러·반복만 있으면 불충분입니다.
2. **질문 의도 우선** — 유저가 묻는 핵심(사실 확인 / 요약 / 비교 / 최신 정보 / 과거 맥락 등)과 각 소스의 정합성을 대조하세요.
3. **소스별 독립 심사** — dom / rag / search를 각각 진단한 뒤, 종합 판정(is_sufficient)을 내리세요.
4. **이미 실행된 엔진 재추천 금지** — `executed_steps`에 있는 엔진은 recommended_action으로 절대 추천하지 마세요.
5. **남은 엔진만 추천** — `pending_engines` 목록에 있는 엔진만 recommended_action 후보입니다.

## 소스별 심사 기준

### context_dom (현장 데이터 — collect_node)
- 사용자가 **현재 보고 있는 화면**에서 질문에 필요한 사실을 추출할 수 있는가?
- 예: 지도 페이지의 장소명·주소·영업시간·리뷰, 기사 본문, 상품 스펙 등
- `empty`: 수집되지 않았거나 빈 문자열
- `not_run`: executed_steps에 collect_node 없음 (아직 미수집)
- `irrelevant`: 텍스트는 있으나 질문 주제와 무관 (CSS 잔여물, 네비 메뉴만 등)
- `insufficient`: 일부 관련 있으나 핵심 사실·수치·근거가 빠짐
- `sufficient`: 질문에 직접 답하는 사실을 현장 데이터만으로 추출 가능

### context_rag (과거 기억 — rag_node)
- "이전에 말했던", "저번에 가려던", "내가 저장한" 등 **개인 맥락** 질문에 부합하는가?
- 과거 대화·스크랩이 질문과 매칭되는가, 아니면 엉뚱한 히트인가?
- `not_run`: executed_steps에 rag_node 없음
- `empty` / `irrelevant` / `insufficient` / `sufficient` — dom과 동일한 엄격도 적용

### context_search (외부 지식 — search_node)
- 최신 트렌드, 영업시간 갱신, 블로그 리뷰, 뉴스, 환율 등 **외부·시간 민감** 정보가 필요한가?
- 검색 결과가 질문에 대한 **구체적 사실**을 담고 있는가, 아니면 일반론·검색 실패 메시지인가?
- `not_run`: executed_steps에 search_node 없음
- `empty` / `irrelevant` / `insufficient` / `sufficient` — 동일

## is_sufficient (종합 판정)
- **True**: 질문 유형에 필요한 소스(들)가 sufficient이거나, irrelevant/not_run인 소스 없이 답변 가능
- **False**: 필수 소스가 empty / insufficient / irrelevant이고, pending_engines로 보완 가능

질문이 여러 소스를 요구하면(예: "이 페이지 요약 + 최신 리뷰 비교") **모든 필수 소스**가 충족되어야 True입니다.

## recommended_action (다음 루프 우선 트리거)
불충분(is_sufficient=False)일 때만 의미 있습니다. **pending_engines에 있는 엔진** 중 하나만 선택:

| 값 | 의미 | 매핑 엔진 |
|----|------|-----------|
| `search` | 외부 최신·보완 정보가 가장 시급 | search_node |
| `rag` | 과거 기억·개인 맥락 보강이 시급 | rag_node |
| `collect` | 현재 화면 DOM/본문 재수집·보강이 시급 | collect_node |
| `none` | 추가 수집 없이 best-effort 답변 (pending 없음, 한도 초과, 또는 보완 불가) |

- is_sufficient=True이면 반드시 `none`
- pending_engines가 비어 있으면 반드시 `none`
- 이미 executed_steps에 있는 엔진에 해당하는 action은 선택 금지

## 출력
Structured Output JSON만 반환하세요. 분석은 reason·각 verdict 필드에 한국어로 작성하세요.
"""

_EVALUATOR_USER_TEMPLATE = """\
[1차 타겟 엔진] {target_engines}
[이미 실행 완료 (재추천 금지)] {executed_steps}
[아직 실행 가능 (pending)] {pending_engines}
[시도 횟수] search={search_attempts}/{max_search}, rag={retrieval_attempts}/{max_retrieval}

[유저 질문]
{user_message}

[활성 탭 제목] {context_title}
[활성 탭 URL] {context_url}

--- 수집된 소스 (소스별 독립 심사) ---

[context_dom — 현장 DOM/페이지 본문]
{context_dom}

[context_rag — 과거 기억/내부 RAG]
{context_rag}

[context_search — 외부 웹 검색]
{context_search}
"""


def build_evaluator_prompt(
    *,
    user_message: str,
    context_title: str,
    context_url: str,
    context_dom: str,
    context_rag: str,
    context_search: str,
    target_engines: list[str],
    executed_steps: list[str],
    pending_engines: list[str],
    search_attempts: int,
    retrieval_attempts: int,
    max_search_attempts: int,
    max_retrieval_attempts: int,
) -> tuple[str, str]:
    """(system_instruction, user_content) 튜플을 반환한다."""
    user_content = _EVALUATOR_USER_TEMPLATE.format(
        target_engines=", ".join(target_engines) if target_engines else "(없음)",
        executed_steps=", ".join(executed_steps) if executed_steps else "(없음)",
        pending_engines=", ".join(pending_engines) if pending_engines else "(없음 — 추가 수집 불가)",
        search_attempts=search_attempts,
        retrieval_attempts=retrieval_attempts,
        max_search=max_search_attempts,
        max_retrieval=max_retrieval_attempts,
        user_message=user_message.strip() or "(빈 질문)",
        context_title=context_title,
        context_url=context_url,
        context_dom=context_dom.strip() or "(수집 없음 — 빈 문자열)",
        context_rag=context_rag.strip() or "(수집 없음 — 빈 문자열)",
        context_search=context_search.strip() or "(수집 없음 — 빈 문자열)",
    )
    return _EVALUATOR_SYSTEM_TEMPLATE, user_content


# 노드명 ↔ action 키워드 (프롬프트·분기 공용 참조)
ENGINE_ACTION_MAP: dict[str, str] = {
    COLLECT_NODE: "collect",
    RAG_NODE: "rag",
    SEARCH_NODE: "search",
}

ACTION_ENGINE_MAP: dict[str, str] = {v: k for k, v in ENGINE_ACTION_MAP.items()}
