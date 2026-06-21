"""Tests for shared.exceptions."""

from __future__ import annotations

from shared.exceptions import (
    APIError,
    ConfigError,
    CrawlError,
    DataForgeError,
    DownloadError,
    NotificationError,
    ParseError,
    PipelineError,
    RateLimitError,
    RobotsError,
    StorageError,
    TransformError,
    ValidationError,
    WarehouseError,
)


def test_crawl_error_has_url() -> None:
    """CrawlError should store the url and status_code attributes."""
    err = CrawlError("failed", url="https://example.com", status_code=503)
    assert err.url == "https://example.com"
    assert err.status_code == 503
    assert str(err) == "failed"


def test_pipeline_error_has_pipeline_id() -> None:
    """PipelineError should carry the pipeline_id."""
    err = PipelineError("orchestration failed", pipeline_id="run-007")
    assert err.pipeline_id == "run-007"
    assert "orchestration failed" in str(err)


def test_validation_error_has_field_and_value() -> None:
    """ValidationError should store field and value."""
    err = ValidationError("bad value", field="price", value=-1)
    assert err.field == "price"
    assert err.value == -1


def test_exception_hierarchy() -> None:
    """All custom exceptions must be instances of DataForgeError."""
    all_errors = [
        ConfigError("cfg"),
        CrawlError("crawl"),
        ParseError("parse"),
        RateLimitError("rate"),
        RobotsError("robots"),
        DownloadError("dl"),
        ValidationError("val"),
        StorageError("storage"),
        WarehouseError("wh"),
        TransformError("xform"),
        PipelineError("pipe"),
        NotificationError("notif"),
        APIError("api"),
    ]
    for err in all_errors:
        assert isinstance(err, DataForgeError), f"{type(err).__name__} not a DataForgeError"


def test_dataforge_error_context() -> None:
    """DataForgeError should store the context dict."""
    ctx = {"key": "value", "count": 42}
    err = DataForgeError("base error", context=ctx)
    assert err.context == ctx


def test_rate_limit_error_attributes() -> None:
    """RateLimitError should set retry_after and status_code=429."""
    err = RateLimitError("too many requests", url="https://api.example.com", retry_after=120)
    assert err.retry_after == 120
    assert err.status_code == 429
    assert err.url == "https://api.example.com"
    assert isinstance(err, CrawlError)


def test_api_error_status_code() -> None:
    """APIError should store the HTTP status code."""
    err = APIError("not found", status_code=404)
    assert err.status_code == 404
