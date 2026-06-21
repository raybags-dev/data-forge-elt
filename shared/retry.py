"""Production Tenacity retry utilities for DataForge ELT.

Usage:
    from shared.retry import build_retry_decorator, RetryPolicy, network_retry

    @network_retry
    def fetch_page(url: str) -> str: ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.exceptions import CrawlError, StorageError

if TYPE_CHECKING:
    import logging

    from loguru import Logger


@dataclass
class RetryPolicy:
    """Configuration for a Tenacity retry strategy.

    Attributes:
        max_attempts: Maximum number of total attempts (including the first).
        wait_min: Minimum wait in seconds between retries (exponential back-off base).
        wait_max: Maximum wait in seconds between retries.
        reraise: Whether to re-raise the final exception after exhausting attempts.
        retry_on: Tuple of exception types that should trigger a retry.
    """

    max_attempts: int = 3
    wait_min: float = 1.0
    wait_max: float = 30.0
    reraise: bool = True
    retry_on: tuple[type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )


def _get_default_policy() -> RetryPolicy:
    """Build a RetryPolicy from application settings (imported lazily to avoid cycles)."""
    from config.settings import get_settings

    s = get_settings()
    return RetryPolicy(
        max_attempts=s.max_retries,
        wait_min=s.retry_wait_min,
        wait_max=s.retry_wait_max,
    )


def build_retry_decorator(
    policy: RetryPolicy,
    logger: "Logger | logging.Logger | None" = None,
) -> Callable:
    """Build a Tenacity ``@retry`` decorator from *policy*.

    Args:
        policy: The retry configuration to apply.
        logger: Optional logger for before-sleep log messages.

    Returns:
        A callable decorator that wraps the target function with retry logic.
    """
    kwargs: dict = {
        "stop": stop_after_attempt(policy.max_attempts),
        "wait": wait_exponential(min=policy.wait_min, max=policy.wait_max),
        "retry": retry_if_exception_type(policy.retry_on),
        "reraise": policy.reraise,
    }
    if logger is not None:
        import logging as stdlib_logging

        if isinstance(logger, stdlib_logging.Logger):
            kwargs["before_sleep"] = before_sleep_log(logger, stdlib_logging.WARNING)
    return retry(**kwargs)


# ── Pre-built decorators ───────────────────────────────────────────────────────

def _build_network_retry() -> Callable:
    """Build the network_retry decorator, imported lazily."""
    try:
        import aiohttp

        network_exceptions: tuple[type[Exception], ...] = (
            httpx.HTTPError,
            aiohttp.ClientError,
            CrawlError,
        )
    except ImportError:
        network_exceptions = (httpx.HTTPError, CrawlError)

    policy = RetryPolicy(
        max_attempts=3,
        wait_min=1.0,
        wait_max=30.0,
        reraise=True,
        retry_on=network_exceptions,
    )
    return build_retry_decorator(policy)


def _build_storage_retry() -> Callable:
    """Build the storage_retry decorator."""
    policy = RetryPolicy(
        max_attempts=3,
        wait_min=0.5,
        wait_max=10.0,
        reraise=True,
        retry_on=(StorageError, OSError, IOError),
    )
    return build_retry_decorator(policy)


network_retry: Callable = _build_network_retry()
storage_retry: Callable = _build_storage_retry()

DEFAULT_RETRY_POLICY: RetryPolicy = RetryPolicy()
