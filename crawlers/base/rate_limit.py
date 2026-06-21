"""Token-bucket rate limiter for the DataForge crawler engine.

Usage::

    limiter = RateLimiter(requests_per_second=2.0)
    await limiter.wait()  # blocks until a token is available
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.settings import Settings


class RateLimiter:
    """Async token-bucket rate limiter.

    Tokens are replenished continuously based on elapsed time.  Callers must
    ``await wait()`` before each outbound request; if no token is available the
    coroutine sleeps for the minimum time required to earn one.

    Attributes:
        requests_per_second: Sustained throughput this limiter enforces.
    """

    def __init__(self, requests_per_second: float) -> None:
        """Initialise the token bucket.

        Args:
            requests_per_second: Target request rate.  Values ≤ 0 are clamped
                to 0.01 to avoid division-by-zero.
        """
        self._rps: float = max(0.01, requests_per_second)
        self._capacity: float = max(1.0, self._rps * 2)
        self._tokens: float = self._capacity
        self._last_refill: float = time.monotonic()
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def requests_per_second(self) -> float:
        """Target request rate enforced by this limiter."""
        return self._rps

    def _refill(self) -> None:
        """Add tokens proportional to the elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rps)
        self._last_refill = now

    async def wait(self) -> None:
        """Block until a request token is available, then consume it.

        Thread-safe via an :class:`asyncio.Lock`.
        """
        async with self._lock:
            self._refill()
            if self._tokens < 1.0:
                sleep_time = (1.0 - self._tokens) / self._rps
                await asyncio.sleep(sleep_time)
                self._refill()
            self._tokens -= 1.0


def build_rate_limiter(settings: Settings) -> RateLimiter:
    """Factory that constructs a :class:`RateLimiter` from application settings.

    Args:
        settings: Pydantic settings instance supplying ``rate_limit_rps``.

    Returns:
        A configured :class:`RateLimiter`.
    """
    return RateLimiter(requests_per_second=settings.rate_limit_rps)
