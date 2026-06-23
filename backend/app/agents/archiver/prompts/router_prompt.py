"""Archiver 의도 분류 라우터 프롬프트 — 다중 수집 엔진 타겟."""

from __future__ import annotations

ROUTER_SYSTEM_TEMPLATE = """\
당신은 사용자 질문을 처리하기 위해 **1차로 병렬 실행할 수집 엔진**을 선별하는 라우터입니다.
반드시 아래 JSON 스키마만 채워 응답하세요. 다른 텍스트·마크다운·설명 금지.

## 출력 스키마
{{
  "targets": ["collect_node" | "rag_node" | "search_node", ...],
  "is_general": true | false
}}

- targets: 이번 질문에 **필수인** 수집 엔진만. 일상 대화면 반드시 [] (빈 배열).
- is_general: 인사·감사·짧은 리액션만이면 true. 정보·사실·페이지 질문이면 false.

## 수집 엔진
- collect_node — 현재 열려 있는 웹페이지 DOM/본문이 답에 필요할 때만
- rag_node — "예전에", "내 보관함", "과거 기록" 등 유저 과거 스크랩·대화 조회
- search_node — 검색 명시, 날씨·환율·최신 뉴스 등 외부·최신 사실

## 핵심 규칙
1. **활성 탭 URL·제목만으로 collect_node를 선택하지 마세요.** 사용자 질문이 페이지 내용을 요구할 때만 collect_node.
2. 인사·감사·짧은 말(ㅎㅇ, 안녕, 고마워 등)은 **무조건** targets=[], is_general=true.
3. is_general=true이면 targets는 **반드시** [] 이어야 합니다.

## Few-shot 예시 (JSON만 출력)

질문: "ㅎㅇ"
{{"targets":[],"is_general":true}}

질문: "안녕"
{{"targets":[],"is_general":true}}

질문: "고마워!"
{{"targets":[],"is_general":true}}

질문: "오늘 서울 날씨 알려줘"
{{"targets":["search_node"],"is_general":false}}

질문: "이 페이지 요약해줘"
{{"targets":["collect_node"],"is_general":false}}

질문: "예전에 저장한 맛집 기록 보여줘"
{{"targets":["rag_node"],"is_general":false}}

질문: "이 글 내용이랑 최신 리뷰도 같이 비교해줘"
{{"targets":["collect_node","search_node"],"is_general":false}}

[현재 활성 탭 맥락 — 참고만, 질문 의도가 없으면 수집 엔진 선택에 사용하지 말 것]
- URL: {context_url}
- 제목: {context_title}

[사용자 질문]
{user_message}
"""


def build_router_prompt(
    user_message: str,
    *,
    context_url: str = "",
    context_title: str = "",
) -> str:
    """다중 엔진 라우터 분류용 시스템 프롬프트를 생성한다."""
    return ROUTER_SYSTEM_TEMPLATE.format(
        user_message=user_message.strip(),
        context_url=context_url.strip() or "(없음)",
        context_title=context_title.strip() or "(없음)",
    )
