"""Tests for shared.retry."""

from __future__ import annotations

import pytest
import httpx

from shared.retry import RetryPolicy, build_retry_decorator, network_retry


def test_build_retry_decorator_retries() -> None:
    """Decorated function should be retried on failure before eventually raising."""
    call_count = 0

    policy = RetryPolicy(max_attempts=3, wait_min=0.0, wait_max=0.0, retry_on=(ValueError,))
    decorated = build_retry_decorator(policy)

    @decorated
    def flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("not yet")
        return "ok"

    result = flaky()
    assert result == "ok"
    assert call_count == 3


def test_retry_respects_max_attempts() -> None:
    """Function should be called exactly max_attempts times before raising."""
    call_count = 0

    policy = RetryPolicy(max_attempts=2, wait_min=0.0, wait_max=0.0, retry_on=(RuntimeError,))
    decorated = build_retry_decorator(policy)

    @decorated
    def always_fails() -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError):
        always_fails()

    assert call_count == 2


def test_network_retry_decorator() -> None:
    """network_retry should be a callable decorator that retries on httpx errors."""
    assert callable(network_retry)

    call_count = 0

    @network_retry
    def fetch() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.ConnectError("connection refused")
        return "data"

    result = fetch()
    assert result == "data"
    assert call_count == 2


def test_retry_policy_defaults() -> None:
    """RetryPolicy should have sensible defaults."""
    policy = RetryPolicy()
    assert policy.max_attempts == 3
    assert policy.wait_min == 1.0
    assert policy.wait_max == 30.0
    assert policy.reraise is True
