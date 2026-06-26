"""OAuth callback redirect — access_denied 등 실패 경로 단위 검증."""

from __future__ import annotations

import sys

from app.services.auth_service import (
    append_query_param,
    encode_oauth_state,
    redirect_oauth_failure,
)


def _assert(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_tests() -> list[str]:
    errors: list[str] = []

    ext_uri = "https://abcdefghij.chromiumapp.org/"
    state = encode_oauth_state({"flow": "extension", "redirect_uri": ext_uri})

    resp = redirect_oauth_failure("access_denied", state)
    location = resp.headers.get("location", "")
    _assert(
        location.startswith(ext_uri) and "error=access_denied" in location,
        "extension flow: access_denied redirect",
        errors,
    )

    web = redirect_oauth_failure("access_denied", None)
    web_loc = web.headers.get("location", "")
    _assert("error=access_denied" in web_loc, "web flow: access_denied redirect", errors)

    _assert(
        append_query_param("https://x.test/cb", "error", "access_denied")
        == "https://x.test/cb?error=access_denied",
        "append_query_param: error",
        errors,
    )

    return errors


def main() -> int:
    errors = run_tests()
    if errors:
        print("[FAIL] auth_test_oauth_redirect")
        for err in errors:
            print(f" - {err}")
        return 1
    print("[PASS] auth_test_oauth_redirect")
    return 0


if __name__ == "__main__":
    sys.exit(main())
