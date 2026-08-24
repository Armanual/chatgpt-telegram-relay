from __future__ import annotations

import hmac


def constant_time_equal(actual: str | None, expected: str | None) -> bool:
    if not actual or not expected:
        return False
    return hmac.compare_digest(actual, expected)


def bearer_value(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    return authorization[len(prefix) :].strip()

