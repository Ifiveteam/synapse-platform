"""Archiver evaluator LLM 프롬프트."""

from __future__ import annotations

from app.agents.archiver.types import ArchiverRoute

EVALUATOR_SYSTEM_TEMPLATE = """\
당신은 Synapse Archiver 에이전트의 '품질 채점관(Evaluator)'입니다.
유저 질문에 답하기 위해 수집된 근거 자료가 **질적·양적으로 충분한지** 판단하세요.

## 판단 기준
1. BASIC: 활성 탭 본문(context_body)이 질문과 직접 관련 있고 사실 추출이 가능한가?
2. RAG: rag_data에 유저 과거 기록이 질문과 관련된 답을 구성할 만큼 있는가?
3. SEARCH: search_data가 최신·외부 정보 질문에 답할 근거를 담고 있는가?
4. 빈 문자열·플레이스홀더·에러 메시지만 있으면 **불충분**으로 본다.
5. RAG 미매칭이면 search 역주행을 우선 고려한다 (search_attempts가 남았을 때).
6. SEARCH/BASIC에서 본문·검색 모두 빈약하면 search 재시도를 고려한다.
7. search_attempts가 최대치에 가까우면 best-effort로 respond를 선택할 수 있다.

## recommended_action 규칙
- respond: 근거가 충분하거나, 추가 수집 없이 최선의 답변을 생성해야 할 때
- search: 외부 검색으로 보완·재시도가 필요할 때
- collect: 내부 RAG 재검색이 의미 있을 때 (RAG 경로 한정)

## 출력
Structured Output 스키마(JSON)만 반환하세요. 설명 문장은 reason 필드에만 작성하세요.
"""

_EVALUATOR_USER_TEMPLATE = """\
[처리 경로] {route}
[검색 시도 횟수] search={search_attempts}, collect={retrieval_attempts}

[유저 질문]
{user_message}

[활성 탭 제목] {context_title}
[활성 탭 URL] {context_url}

[context_body — BASIC 수집]
{context_body}

[rag_data — 내부 RAG]
{rag_data}

[search_data — 웹 검색]
{search_data}
"""


def build_evaluator_prompt(
    *,
    route: ArchiverRoute,
    user_message: str,
    context_title: str,
    context_url: str,
    context_body: str,
    rag_data: str,
    search_data: str,
    search_attempts: int,
    retrieval_attempts: int,
) -> tuple[str, str]:
    """(system_instruction, user_content) 튜플을 반환한다."""
    user_content = _EVALUATOR_USER_TEMPLATE.format(
        route=route.value,
        search_attempts=search_attempts,
        retrieval_attempts=retrieval_attempts,
        user_message=user_message.strip() or "(빈 질문)",
        context_title=context_title,
        context_url=context_url,
        context_body=context_body.strip() or "(없음)",
        rag_data=rag_data.strip() or "(없음)",
        search_data=search_data.strip() or "(없음)",
    )
    return EVALUATOR_SYSTEM_TEMPLATE, user_content
