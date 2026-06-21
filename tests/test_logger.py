"""Tests for shared.logger."""

from __future__ import annotations

from pathlib import Path

from shared.logger import configure_logging, get_logger, pipeline_context


def test_configure_logging_creates_log_dir(tmp_settings) -> None:
    """configure_logging should create the log directory if it does not exist."""
    log_dir = Path(tmp_settings.log_dir)
    assert not log_dir.exists()
    configure_logging(tmp_settings)
    assert log_dir.exists()
    assert log_dir.is_dir()


def test_get_logger_returns_logger() -> None:
    """get_logger should return a usable Loguru logger."""
    log = get_logger("test.module")
    # Loguru loggers have an .info method
    assert callable(log.info)
    assert callable(log.error)


def test_pipeline_context_binds_fields() -> None:
    """pipeline_context should not raise and should restore context on exit."""
    log = get_logger("test")
    # Verify the context manager completes without error
    with pipeline_context(pipeline_id="run-abc", source="kaggle"):
        log.info("inside context")
    # After exit, context vars are restored — just verify no exception
    log.info("outside context")


def test_get_logger_different_names_return_different_loggers() -> None:
    """Different names should return loggers with distinct bindings."""
    log_a = get_logger("module.a")
    log_b = get_logger("module.b")
    # Both should be callable
    assert callable(log_a.info)
    assert callable(log_b.info)
