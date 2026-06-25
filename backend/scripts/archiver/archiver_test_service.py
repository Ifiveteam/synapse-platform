"""Archiver Service 계층 테스트 — token 격리·assistant 로그 영속 정책."""

from __future__ import annotations

import sys

from app.agents.archiver.core.constants import STREAM_ERROR_MESSAGE
from app.agents.archiver.models import ArchiverStreamEvent
from app.services.archiver_service import (
    collect_token_chunks,
    join_assistant_tokens,
    should_persist_assistant_log,
)


def _assert(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_service_tests() -> list[str]:
    errors: list[str] = []

    events = [
        ArchiverStreamEvent(event="status", content="🔀 [Router] 안내\n\n"),
        ArchiverStreamEvent(event="token", content="답변 "),
        ArchiverStreamEvent(event="status", content="✨ [Respond] 생성 중\n\n"),
        ArchiverStreamEvent(event="token", content="본문"),
    ]
    tokens = collect_token_chunks(events)
    _assert(tokens == ["답변 ", "본문"], "collect_token_chunks: status 제외", errors)
    _assert(
        join_assistant_tokens(tokens) == "답변 본문",
        "join_assistant_tokens: 합본",
        errors,
    )
    _assert(
        should_persist_assistant_log("답변 본문") is True,
        "persist: 정상 답변 저장",
        errors,
    )
    _assert(
        should_persist_assistant_log("") is False,
        "persist: 빈 문자열 스킵",
        errors,
    )
    _assert(
        should_persist_assistant_log("   ") is False,
        "persist: 공백만 스킵",
        errors,
    )
    _assert(
        should_persist_assistant_log(STREAM_ERROR_MESSAGE) is False,
        "persist: STREAM_ERROR_MESSAGE DB 미저장",
        errors,
    )
    _assert(
        should_persist_assistant_log(f"{STREAM_ERROR_MESSAGE} (detail)") is False,
        "persist: 오류 prefix 변형도 미저장",
        errors,
    )

    # status만 있는 스트림은 DB assistant 본문이 비어야 함
    status_only = collect_token_chunks(
        [ArchiverStreamEvent(event="status", content="진행 안내")]
    )
    _assert(status_only == [], "status-only stream: token 없음", errors)
    _assert(
        should_persist_assistant_log(join_assistant_tokens(status_only)) is False,
        "status-only stream: DB 저장 스킵",
        errors,
    )

    return errors


def main() -> int:
    errors = run_service_tests()
    if errors:
        print("[FAIL] archiver_test_service")
        for err in errors:
            print(f" - {err}")
        return 1
    print("[PASS] archiver_test_service")
    return 0


if __name__ == "__main__":
    sys.exit(main())
