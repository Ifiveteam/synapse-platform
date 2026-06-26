"""need_dom 스텝 — 클라이언트 DOM 수집을 요청하고 그래프 실행을 일시 중단한다.

## 아키텍처: `steps/`에 두는 이유 (`nodes/`가 아님)

| 구분 | need_dom | collect_node (nodes/) |
|------|----------|------------------------|
| State | `current_step`만 갱신, 근거 필드 미작성 | `context_dom` 등 근거 데이터 채움 |
| I/O | SSE `need_dom` 이벤트 방출 (프로토콜 브릿지) | HTTP 스크래핑·Store 검색·Search Tool |
| 그래프 | `need_dom → END` — 1차 스트림 종료 후 클라이언트 2차 요청 대기 | fan-out 엔진 → evaluator fan-in |
| 판단 주체 | router(`classify`)가 선행 분기 결정 | evaluator 루프에서 재수집 여부 결정 |

이 노드는 **데이터를 수집하지 않는다**. 익스텐션이 DOM을 채워 재요청(`dom_continuation`)할 때까지
서버 실행을 끊는 **오케스트레이션·클라이언트 제어** 역할이므로 `steps/`에 둔다.
"""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer

from app.agents.archiver.protocols.stream_status import need_dom_event
from app.agents.archiver.trace import log_node_enter
from app.agents.archiver.models import ArchiverState


async def need_dom(state: ArchiverState) -> dict[str, Any]:
    """context_body 없이 BASIC으로 분류된 경우 익스텐션에 DOM 수집을 요청한다."""
    log_node_enter("need_dom", state=state)

    writer = get_stream_writer()
    writer(need_dom_event())

    return {"current_step": "need_dom"}
