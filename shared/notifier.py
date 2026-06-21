"""Notification abstractions for DataForge ELT.

Supports Console, Discord, Slack, Email, and multi-channel fan-out.
Notification failures are always logged — they never crash the pipeline.

Usage:
    from shared.notifier import NotifierFactory, NotificationPayload, NotificationLevel

    notifier = NotifierFactory.build_notifier(settings)
    notifier.send(NotificationPayload(title="Done", message="Pipeline finished", level=NotificationLevel.INFO))
"""

from __future__ import annotations

import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import TYPE_CHECKING

import httpx
from rich.console import Console
from rich.panel import Panel

from shared.logger import get_logger

if TYPE_CHECKING:
    from config.settings import Settings

_log = get_logger(__name__)
_console = Console()


class NotificationLevel(Enum):
    """Severity level for a notification payload."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class NotificationPayload:
    """Structured notification message.

    Attributes:
        title: Short summary title.
        message: Detailed message body.
        level: Severity of the notification.
        pipeline_id: Optional pipeline run identifier.
        details: Optional structured metadata dict.
    """

    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    pipeline_id: str | None = None
    details: dict | None = field(default=None)


class Notifier(ABC):
    """Abstract base class for all notification channels."""

    @abstractmethod
    def send(self, payload: NotificationPayload) -> None:
        """Deliver *payload* via this channel.

        Args:
            payload: The notification to send.
        """


class ConsoleNotifier(Notifier):
    """Prints rich-formatted notifications to stdout."""

    _LEVEL_STYLES: dict[NotificationLevel, str] = {
        NotificationLevel.INFO: "blue",
        NotificationLevel.WARNING: "yellow",
        NotificationLevel.ERROR: "red",
        NotificationLevel.CRITICAL: "bold red",
    }

    def send(self, payload: NotificationPayload) -> None:
        """Print *payload* to the console with colour-coded level."""
        style = self._LEVEL_STYLES.get(payload.level, "white")
        body = payload.message
        if payload.pipeline_id:
            body = f"[dim]pipeline_id={payload.pipeline_id}[/dim]\n{body}"
        if payload.details:
            body += f"\n{payload.details}"
        _console.print(
            Panel(body, title=f"[{style}]{payload.title}[/{style}]", border_style=style)
        )


class DiscordNotifier(Notifier):
    """Posts notifications to a Discord webhook with level-coloured embeds."""

    _LEVEL_COLORS: dict[NotificationLevel, int] = {
        NotificationLevel.INFO: 0x3498DB,
        NotificationLevel.WARNING: 0xF39C12,
        NotificationLevel.ERROR: 0xE74C3C,
        NotificationLevel.CRITICAL: 0x8E44AD,
    }

    def __init__(self, webhook_url: str) -> None:
        """Args:
            webhook_url: Discord incoming webhook URL.
        """
        self._webhook_url = webhook_url

    def send(self, payload: NotificationPayload) -> None:
        """Post *payload* as a Discord embed message."""
        color = self._LEVEL_COLORS.get(payload.level, 0xAAAAAA)
        embed: dict = {
            "title": payload.title,
            "description": payload.message,
            "color": color,
            "fields": [],
        }
        if payload.pipeline_id:
            embed["fields"].append({"name": "pipeline_id", "value": payload.pipeline_id})
        if payload.details:
            for key, val in payload.details.items():
                embed["fields"].append({"name": str(key), "value": str(val), "inline": True})
        try:
            response = httpx.post(self._webhook_url, json={"embeds": [embed]}, timeout=10)
            response.raise_for_status()
        except Exception as exc:
            _log.error(f"DiscordNotifier failed: {exc}")


class SlackNotifier(Notifier):
    """Posts notifications to a Slack incoming webhook."""

    def __init__(self, webhook_url: str) -> None:
        """Args:
            webhook_url: Slack incoming webhook URL.
        """
        self._webhook_url = webhook_url

    def _build_text(self, payload: NotificationPayload) -> str:
        """Format *payload* as a Slack-compatible text block."""
        lines = [f"*{payload.title}* [{payload.level.value}]", payload.message]
        if payload.pipeline_id:
            lines.append(f"pipeline_id: `{payload.pipeline_id}`")
        if payload.details:
            lines.append(str(payload.details))
        return "\n".join(lines)

    def send(self, payload: NotificationPayload) -> None:
        """Post *payload* to the Slack webhook."""
        try:
            response = httpx.post(
                self._webhook_url,
                json={"text": self._build_text(payload)},
                timeout=10,
            )
            response.raise_for_status()
        except Exception as exc:
            _log.error(f"SlackNotifier failed: {exc}")


class EmailNotifier(Notifier):
    """Sends notifications via SMTP with TLS."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
        to_addr: str,
    ) -> None:
        """Args:
            host: SMTP server hostname.
            port: SMTP server port (typically 587 for TLS).
            user: SMTP username / login.
            password: SMTP password.
            from_addr: Sender email address.
            to_addr: Recipient email address.
        """
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = from_addr
        self._to = to_addr

    def _build_email(self, payload: NotificationPayload) -> MIMEMultipart:
        """Construct the MIME message from *payload*."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[DataForge][{payload.level.value}] {payload.title}"
        msg["From"] = self._from
        msg["To"] = self._to
        body = payload.message
        if payload.pipeline_id:
            body += f"\n\npipeline_id: {payload.pipeline_id}"
        if payload.details:
            body += f"\n\nDetails: {payload.details}"
        msg.attach(MIMEText(body, "plain"))
        return msg

    def send(self, payload: NotificationPayload) -> None:
        """Send *payload* via SMTP TLS."""
        try:
            msg = self._build_email(payload)
            with smtplib.SMTP(self._host, self._port) as server:
                server.ehlo()
                server.starttls()
                server.login(self._user, self._password)
                server.sendmail(self._from, self._to, msg.as_string())
        except Exception as exc:
            _log.error(f"EmailNotifier failed: {exc}")


class MultiNotifier(Notifier):
    """Fans out a notification to all registered child notifiers.

    Args:
        notifiers: List of Notifier instances to deliver to.
    """

    def __init__(self, notifiers: list[Notifier]) -> None:
        self._notifiers = notifiers

    @property
    def notifiers(self) -> list[Notifier]:
        """Return the list of registered child notifiers."""
        return self._notifiers

    def send(self, payload: NotificationPayload) -> None:
        """Deliver *payload* to every child notifier."""
        for notifier in self._notifiers:
            notifier.send(payload)


class NotifierFactory:
    """Factory that assembles a MultiNotifier from application settings."""

    @staticmethod
    def build_notifier(settings: Settings) -> Notifier:
        """Create a MultiNotifier with all configured channels.

        Always includes ConsoleNotifier. Adds Discord, Slack, and Email
        notifiers when the required settings are present.

        Args:
            settings: Application settings instance.

        Returns:
            A MultiNotifier (or single ConsoleNotifier) ready for use.
        """
        notifiers: list[Notifier] = [ConsoleNotifier()]

        if settings.discord_webhook:
            notifiers.append(DiscordNotifier(settings.discord_webhook))

        if settings.slack_webhook:
            notifiers.append(SlackNotifier(settings.slack_webhook))

        if settings.email_host and settings.email_user:
            notifiers.append(
                EmailNotifier(
                    host=settings.email_host,
                    port=settings.email_port,
                    user=settings.email_user,
                    password=settings.email_password or "",
                    from_addr=settings.email_from,
                    to_addr=settings.email_to or settings.email_user,
                )
            )

        return MultiNotifier(notifiers)
