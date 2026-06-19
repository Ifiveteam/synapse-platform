"""Archiver 테스트 러너 — unit · service · runtime smoke 일괄 실행."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        msg = f"cannot load module from {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    scripts_dir = Path(__file__).resolve().parent
    results: list[tuple[str, int]] = []

    unit = _load_module("archiver_test_unit", scripts_dir / "archiver_test_unit.py")
    results.append(("unit", unit.main()))

    service = _load_module(
        "archiver_test_service",
        scripts_dir / "archiver_test_service.py",
    )
    results.append(("service", service.main()))

    smoke = _load_module("archiver_smoke", scripts_dir / "archiver_smoke.py")
    results.append(("smoke", asyncio.run(smoke.main())))

    p2 = _load_module("archiver_test_p2", scripts_dir / "archiver_test_p2.py")
    results.append(("p2", p2.main()))

    failed = [name for name, code in results if code != 0]
    print("\n--- archiver test summary ---")
    for name, code in results:
        print(f"  {name}: {'PASS' if code == 0 else 'FAIL'}")

    if failed:
        print(f"\n[FAIL] failed suites: {', '.join(failed)}")
        return 1

    print("\n[PASS] all archiver test suites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
