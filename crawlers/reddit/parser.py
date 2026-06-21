"""HTML parser for Reddit (old-style reddit.com interface).

Targets the classic ``old.reddit.com`` layout which exposes stable CSS
classes such as ``.thing``, ``.title``, ``.author``, and ``.score``.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from crawlers.base.models import CrawledPage
from crawlers.reddit.models import RedditPost
from shared.logger import get_logger

_log = get_logger(__name__)

_PARSERS = ["lxml", "html.parser"]


def _make_soup(html: str) -> BeautifulSoup:
    """Return a BeautifulSoup tree, preferring lxml."""
    for parser in _PARSERS:
        try:
            return BeautifulSoup(html, parser)
        except Exception:
            continue
    return BeautifulSoup(html, "html.parser")


class RedditParser:
    """Parses old.reddit.com listing pages into :class:`RedditPost` records.

    All parse errors are absorbed and logged — the parser never raises.
    """

    def parse_page(self, page: CrawledPage) -> list[RedditPost]:
        """Extract all posts visible on *page*.

        Args:
            page: Fetched page snapshot.

        Returns:
            List of :class:`RedditPost` objects (may be empty).
        """
        try:
            soup = _make_soup(page.html)
            return self._extract_posts(soup, page.url)
        except Exception as exc:
            _log.warning("RedditParser failed on {url}: {exc}", url=page.url, exc=exc)
            return []

    def _extract_posts(self, soup: BeautifulSoup, base_url: str) -> list[RedditPost]:
        """Find all ``.thing`` elements and parse each one."""
        things = soup.select("div.thing.link")
        if not things:
            things = soup.select("[data-type='link']")
        posts: list[RedditPost] = []
        for element in things:
            post = self.parse_item(element)
            if post is not None:
                posts.append(post)
        return posts

    def parse_item(self, element: Tag) -> RedditPost | None:
        """Parse a single post element into a :class:`RedditPost`.

        Args:
            element: A ``<div class="thing">`` Tag from BeautifulSoup.

        Returns:
            A :class:`RedditPost` or ``None`` if parsing fails.
        """
        try:
            return self._build_post(element)
        except Exception as exc:
            _log.debug("Skipping malformed post element: {exc}", exc=exc)
            return None

    def _build_post(self, el: Tag) -> RedditPost:
        """Extract fields from a post element and construct a RedditPost."""
        post_id = el.get("data-fullname", "") or el.get("id", "")
        subreddit = el.get("data-subreddit", "")
        author = el.get("data-author", "")
        score_str = el.get("data-score", "0") or "0"

        title_el = el.select_one("a.title") or el.select_one(".title > a")
        title = title_el.get_text(strip=True) if title_el else ""
        url = title_el.get("href", "") if title_el else ""

        score = self._safe_int(score_str)

        comments_el = el.select_one("a.comments")
        num_comments = 0
        if comments_el:
            text = comments_el.get_text(strip=True).split()[0]
            num_comments = self._safe_int(text)

        time_el = el.select_one("time")
        created_utc: datetime | None = None
        if time_el and time_el.get("datetime"):
            with contextlib.suppress(ValueError):
                created_utc = datetime.fromisoformat(
                    str(time_el["datetime"]).replace("Z", "+00:00")
                )

        return RedditPost(
            id=str(post_id),
            title=title,
            author=str(author),
            subreddit=str(subreddit),
            score=score,
            num_comments=num_comments,
            url=str(url),
            created_utc=created_utc,
        )

    @staticmethod
    def _safe_int(value: Any) -> int:
        """Convert *value* to int, returning 0 on failure."""
        try:
            return int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0
