"""Login brute-force throttling.

In-process only — a real multi-instance deployment needs a shared store
(Redis is already configured via REDIS_URL for other purposes) for this to
hold across processes. This is still a real improvement over the previous
"nothing at all", and matches the single-process deployment this app ships
with today; sharing it via Redis is a mechanical follow-up, not a redesign.

Deliberately a cooldown, not a permanent lockout: a hard per-username lockout
would let an attacker deny service to a real officer just by repeatedly
failing their username from anywhere. This self-heals after the cooldown
window instead.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class _Attempts:
    failures: list[float] = field(default_factory=list)


class LoginRateLimiter:
    def __init__(
        self,
        *,
        max_failures: int = 5,
        window_seconds: float = 900.0,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._attempts: dict[str, _Attempts] = defaultdict(_Attempts)

    def _prune(self, key: str, now: float) -> list[float]:
        entry = self._attempts[key]
        entry.failures = [t for t in entry.failures if now - t < self.window_seconds]
        return entry.failures

    def seconds_until_allowed(self, key: str) -> float:
        """0.0 if the next attempt for `key` is allowed right now, otherwise
        how many seconds until it is."""
        now = time.monotonic()
        failures = self._prune(key, now)
        if len(failures) < self.max_failures:
            return 0.0
        remaining = self.cooldown_seconds - (now - failures[-1])
        return max(0.0, remaining)

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        self._prune(key, now)
        self._attempts[key].failures.append(now)

    def record_success(self, key: str) -> None:
        self._attempts.pop(key, None)


def _build_default_limiter() -> LoginRateLimiter:
    from app.config import get_settings

    settings = get_settings()
    return LoginRateLimiter(
        max_failures=settings.login_max_failures,
        window_seconds=settings.login_window_seconds,
        cooldown_seconds=settings.login_cooldown_seconds,
    )


_default_limiter = _build_default_limiter()


def get_default_limiter() -> LoginRateLimiter:
    return _default_limiter
