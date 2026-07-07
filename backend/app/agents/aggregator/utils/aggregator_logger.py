"""어그리게이터 배치 매핑 전용 구조화 로깅."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator, Literal

LayerName = Literal["scrap", "youtube", "behavior"]
ModeName = Literal["shortcut", "llm", "grounding"]

_DEFAULT_LOGGER_NAME = "app.agents.aggregator.mapper"


class AggregatorLogger:
    """레이어별 숏컷/LLM/Grounding 호출·지연 시간 추적."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(_DEFAULT_LOGGER_NAME)
        self._starts: dict[str, float] = {}

    def _event_key(self, layer: LayerName, mode: ModeName, operation: str) -> str:
        return f"{layer}:{mode}:{operation}"

    @contextmanager
    def track(
        self,
        layer: LayerName,
        mode: ModeName,
        *,
        operation: str = "classify",
        **context: Any,
    ) -> Iterator[None]:
        """컨텍스트 매니저 — 성공/실패 시 latency_ms 자동 기록."""
        key = self._event_key(layer, mode, operation)
        self.log_start(layer, mode, operation=operation, **context)
        self._starts[key] = time.perf_counter()
        try:
            yield
        except Exception as exc:
            latency_ms = self._elapsed_ms(key)
            self.log_failure(
                layer,
                mode,
                operation=operation,
                latency_ms=latency_ms,
                error=exc,
                **context,
            )
            raise
        finally:
            self._starts.pop(key, None)

    def _elapsed_ms(self, key: str) -> float:
        started = self._starts.get(key)
        if started is None:
            return 0.0
        return round((time.perf_counter() - started) * 1000, 2)

    def log_start(
        self,
        layer: LayerName,
        mode: ModeName,
        *,
        operation: str = "classify",
        **context: Any,
    ) -> None:
        self._logger.info(
            "[aggregator][%s][%s] %s 시작 %s",
            layer,
            mode,
            operation,
            self._format_context(context),
        )

    def log_success(
        self,
        layer: LayerName,
        mode: ModeName,
        *,
        operation: str = "classify",
        latency_ms: float,
        result_summary: str | None = None,
        **context: Any,
    ) -> None:
        extra = self._format_context(context)
        if result_summary:
            extra = (
                f"{extra} result={result_summary}"
                if extra
                else f"result={result_summary}"
            )
        self._logger.info(
            "[aggregator][%s][%s] %s 성공 latency_ms=%.2f %s",
            layer,
            mode,
            operation,
            latency_ms,
            extra,
        )

    def log_failure(
        self,
        layer: LayerName,
        mode: ModeName,
        *,
        operation: str = "classify",
        latency_ms: float,
        error: BaseException,
        **context: Any,
    ) -> None:
        self._logger.exception(
            "[aggregator][%s][%s] %s 실패 latency_ms=%.2f error=%s %s",
            layer,
            mode,
            operation,
            latency_ms,
            error,
            self._format_context(context),
        )

    def log_shortcut_hit(
        self,
        layer: LayerName,
        *,
        latency_ms: float,
        result_summary: str,
        **context: Any,
    ) -> None:
        self.log_success(
            layer,
            "shortcut",
            latency_ms=latency_ms,
            result_summary=result_summary,
            **context,
        )

    def log_llm_invoked(
        self,
        layer: LayerName,
        *,
        reason: str,
        **context: Any,
    ) -> None:
        self._logger.info(
            "[aggregator][%s][llm] 호출 사유=%s %s",
            layer,
            reason,
            self._format_context(context),
        )

    def log_grounding_invoked(
        self,
        layer: LayerName,
        *,
        reason: str,
        **context: Any,
    ) -> None:
        self._logger.info(
            "[aggregator][%s][grounding] Google Search Grounding 활성화 사유=%s %s",
            layer,
            reason,
            self._format_context(context),
        )

    def begin_timer(
        self, layer: LayerName, mode: ModeName, operation: str = "classify"
    ) -> str:
        key = self._event_key(layer, mode, operation)
        self._starts[key] = time.perf_counter()
        return key

    def end_timer(self, key: str) -> float:
        latency_ms = self._elapsed_ms(key)
        self._starts.pop(key, None)
        return latency_ms

    @staticmethod
    def summarize_scores(scores: dict[Any, float] | None) -> str:
        if not scores:
            return "{}"
        parts = [f"{domain}={weight:.3f}" for domain, weight in scores.items()]
        return "{" + ", ".join(parts) + "}"

    @staticmethod
    def _format_context(context: dict[str, Any]) -> str:
        if not context:
            return ""
        pairs = [f"{key}={value!r}" for key, value in context.items()]
        return " ".join(pairs)
