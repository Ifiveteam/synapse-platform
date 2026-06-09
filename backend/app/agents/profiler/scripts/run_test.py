"""Profiler local test runner.

Usage (from backend/):
  uv run python -m app.agents.profiler.scripts.run_test
  uv run python -m app.agents.profiler.scripts.run_test mock_jiyeon
  uv run python -m app.agents.profiler.scripts.run_test --all
  uv run python -m app.agents.profiler.scripts.run_test mock_jiyeon --json
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

from app.agents.profiler.base import ProfilerResult
from app.agents.profiler.graph import run_profiler
from app.agents.profiler.subagent.load_records.loader import list_personas

EXPECTED_STEP = "notify"
DEFAULT_TEST_EMAIL = "test@ifive.site"


def _final_to_result(user_id: str, final: dict) -> ProfilerResult:
    return ProfilerResult(
        user_id=user_id,
        computed_at=datetime.now(UTC),
        axes=final["axes"],
        layer_b=final["layer_b"],
        top5_interests=final["top5_interests"],
        summary=final["summary"],
        interpretation=final["interpretation"],
        axis_notes=final.get("axis_notes", {}),
        investigation_log=final.get("investigation_log", []),
        llm_used=final.get("llm_used", False),
        behavior_patterns=final.get("behavior_patterns"),
    )


def _assert_pipeline(final: dict) -> list[str]:
    errors: list[str] = []
    if final.get("current_step") != EXPECTED_STEP:
        errors.append(
            f"current_step={final.get('current_step')!r}, expected {EXPECTED_STEP!r}"
        )
    for key in ("axes", "layer_b", "top5_interests", "summary", "interpretation"):
        if key not in final:
            errors.append(f"missing key: {key}")
    if not final.get("summary", "").strip():
        errors.append("summary is empty")
    if "notification" not in final:
        errors.append("missing key: notification")
    return errors


def _print_summary(result: ProfilerResult) -> None:
    i = result.interpretation
    print(f"user_id       : {result.user_id}")
    print(f"llm_used      : {result.llm_used}")
    print(f"layer_b       : {result.layer_b.model_dump()}")
    print(f"interpretation: {i.model_dump()}")
    print(f"top5          : {len(result.top5_interests)} items")
    if result.behavior_patterns:
        print(f"patterns      : {result.behavior_patterns.model_dump()}")
    print(f"summary       : {result.summary[:120]}...")


def run_one(user_id: str, *, as_json: bool = False) -> ProfilerResult:
    test_email = os.getenv("PROFILER_TEST_EMAIL", DEFAULT_TEST_EMAIL)
    final = run_profiler(user_id, test_email)
    errors = _assert_pipeline(final)
    result = _final_to_result(user_id, final)

    if errors:
        msg = "; ".join(errors)
        raise RuntimeError(f"Profiler test failed for {user_id}: {msg}")

    if as_json:
        print(result.model_dump_json(indent=2))
    else:
        _print_summary(result)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Profiler pipeline on mock personas",
    )
    parser.add_argument(
        "user_id",
        nargs="?",
        default="mock_jiyeon",
        help="mock user id (default: mock_jiyeon)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="run all personas from mocks/manifest.json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print full ProfilerResult JSON",
    )
    args = parser.parse_args(argv)

    user_ids = [p.id for p in list_personas()] if args.all else [args.user_id]

    failed = 0
    for user_id in user_ids:
        if args.all and not args.json:
            print(f"\n--- {user_id} ---")
        try:
            run_one(user_id, as_json=args.json)
        except Exception as exc:  # noqa: BLE001 — CLI test runner
            failed += 1
            print(f"FAIL {user_id}: {exc}", file=sys.stderr)

    if failed:
        print(f"\n{failed}/{len(user_ids)} failed", file=sys.stderr)
        return 1

    if args.all and not args.json:
        print(f"\nOK - {len(user_ids)} persona(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
