"""Tests for shared.notifier."""

from __future__ import annotations

from shared.notifier import (
    ConsoleNotifier,
    DiscordNotifier,
    MultiNotifier,
    NotificationLevel,
    NotificationPayload,
    NotifierFactory,
    SlackNotifier,
)


def _make_payload(level: NotificationLevel = NotificationLevel.INFO) -> NotificationPayload:
    return NotificationPayload(
        title="Test",
        message="Test message",
        level=level,
        pipeline_id="run-test",
    )


def test_console_notifier_sends() -> None:
    """ConsoleNotifier.send() should not raise for any level."""
    notifier = ConsoleNotifier()
    for level in NotificationLevel:
        notifier.send(_make_payload(level))  # must not raise


def test_multi_notifier_fans_out(mock_notifier) -> None:
    """MultiNotifier should call send() on every child notifier."""
    from tests.conftest import _MockNotifier

    child_a = _MockNotifier()
    child_b = _MockNotifier()
    multi = MultiNotifier([child_a, child_b])

    payload = _make_payload()
    multi.send(payload)

    assert len(child_a.calls) == 1
    assert len(child_b.calls) == 1
    assert child_a.calls[0] is payload
    assert child_b.calls[0] is payload


def test_notifier_factory_always_includes_console(tmp_settings) -> None:
    """build_notifier() must always include at least a ConsoleNotifier."""
    notifier = NotifierFactory.build_notifier(tmp_settings)
    assert isinstance(notifier, MultiNotifier)
    assert any(isinstance(n, ConsoleNotifier) for n in notifier.notifiers)


def test_discord_notifier_skipped_when_no_webhook(tmp_settings) -> None:
    """No DiscordNotifier should be added when discord_webhook is unset."""
    # tmp_settings has no discord_webhook
    notifier = NotifierFactory.build_notifier(tmp_settings)
    assert isinstance(notifier, MultiNotifier)
    assert not any(isinstance(n, DiscordNotifier) for n in notifier.notifiers)


def test_slack_notifier_skipped_when_no_webhook(tmp_settings) -> None:
    """No SlackNotifier should be added when slack_webhook is unset."""
    notifier = NotifierFactory.build_notifier(tmp_settings)
    assert not any(isinstance(n, SlackNotifier) for n in notifier.notifiers)


def test_multi_notifier_with_details() -> None:
    """MultiNotifier should pass details through to children."""
    from tests.conftest import _MockNotifier

    child = _MockNotifier()
    multi = MultiNotifier([child])
    payload = NotificationPayload(
        title="With Details",
        message="body",
        level=NotificationLevel.ERROR,
        details={"rows_failed": 5, "source": "kaggle"},
    )
    multi.send(payload)
    assert child.calls[0].details == {"rows_failed": 5, "source": "kaggle"}
