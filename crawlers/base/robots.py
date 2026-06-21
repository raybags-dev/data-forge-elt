"""Robots.txt compliance checker for the DataForge crawler engine.

Fetches and caches ``robots.txt`` per domain; uses
:mod:`urllib.robotparser` for rule evaluation.  Fails open — if the
robots file cannot be fetched the URL is assumed to be allowed.
"""

from __future__ import annotations

import urllib.robotparser
from urllib.parse import urlparse

import httpx

from shared.logger import get_logger

_log = get_logger(__name__)


class RobotsChecker:
    """Async robots.txt compliance checker with per-domain caching.

    Attributes:
        user_agent: The crawler user-agent string used to look up rules.
        enabled: When ``False`` every URL is permitted without fetching.
    """

    def __init__(self, user_agent: str = "*", enabled: bool = True) -> None:
        """Initialise the checker.

        Args:
            user_agent: User-agent token sent to the robots parser.
            enabled: Toggle compliance checking on/off.
        """
        self.user_agent: str = user_agent
        self.enabled: bool = enabled
        # Maps domain → parser (or None when the fetch failed — fail-open)
        self._cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _robots_url(self, url: str) -> str:
        """Derive the robots.txt URL for the given *url*'s domain."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    async def _fetch_parser(
        self, domain: str, robots_url: str
    ) -> urllib.robotparser.RobotFileParser | None:
        """Download *robots_url* and return a parsed :class:`RobotFileParser`.

        Returns ``None`` on any fetch or parse failure so the caller can
        fail-open without relying on uninitialised parser behaviour.

        Args:
            domain: Domain key used for caching.
            robots_url: Full URL of the robots.txt resource.
        """
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    parser.parse(response.text.splitlines())
                    return parser
                _log.debug(
                    "robots.txt not found for {domain} (HTTP {code})",
                    domain=domain,
                    code=response.status_code,
                )
                return None
        except Exception as exc:
            _log.warning(
                "Could not fetch robots.txt for {domain}: {exc}",
                domain=domain,
                exc=exc,
            )
            return None

    async def is_allowed(self, url: str) -> bool:
        """Return ``True`` if *url* is permitted for this crawler's user-agent.

        Fails open: if the robots.txt cannot be fetched, the URL is allowed.

        Args:
            url: The URL to check.

        Returns:
            ``True`` when crawling is allowed, compliance is disabled, or the
            robots.txt file could not be retrieved.
        """
        if not self.enabled:
            return True

        parsed = urlparse(url)
        domain = parsed.netloc

        if domain not in self._cache:
            robots_url = self._robots_url(url)
            self._cache[domain] = await self._fetch_parser(domain, robots_url)

        parser = self._cache[domain]
        if parser is None:
            # Fetch failed — fail open
            return True

        allowed: bool = parser.can_fetch(self.user_agent, url)
        if not allowed:
            _log.info(
                "robots.txt disallows {url} for agent '{agent}'",
                url=url,
                agent=self.user_agent,
            )
        return allowed
