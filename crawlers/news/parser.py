"""HTML parser for generic news article pages.

Targets common news site conventions:
- ``<article>`` element for the article body
- ``<h1>`` for the headline
- ``.author`` / ``[rel='author']`` for bylines
- ``<time datetime="...">`` for publication timestamps
- ``.article-body`` / ``.article-content`` for body text
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from crawlers.base.models import CrawledPage
from crawlers.news.models import NewsArticle
from shared.logger import get_logger

_log = get_logger(__name__)
_PARSERS = ["lxml", "html.parser"]


def _make_soup(html: str) -> BeautifulSoup:
    for parser in _PARSERS:
        try:
            return BeautifulSoup(html, parser)
        except Exception:
            continue
    return BeautifulSoup(html, "html.parser")


class NewsParser:
    """Parses generic news HTML pages into :class:`NewsArticle` records."""

    def parse_page(self, page: CrawledPage) -> list[NewsArticle]:
        """Extract article records from *page*.

        Args:
            page: Fetched page snapshot.

        Returns:
            List of :class:`NewsArticle` objects (may be empty).
        """
        try:
            soup = _make_soup(page.html)
            return self._extract_articles(soup, page.url)
        except Exception as exc:
            _log.warning("NewsParser failed on {url}: {exc}", url=page.url, exc=exc)
            return []

    def _extract_articles(
        self, soup: BeautifulSoup, url: str
    ) -> list[NewsArticle]:
        """Detect whether this is a listing or article page and parse accordingly."""
        # Try article detail page first
        article_el = soup.select_one("article")
        h1 = soup.select_one("h1")
        if h1 and article_el:
            item = self.parse_item(soup.find("body") or soup)
            return [item] if item else []

        # Listing page: extract article cards
        cards = soup.select("article, .article-card, .story, .post")
        if cards:
            return [a for card in cards if (a := self.parse_item(card)) is not None]

        return []

    def parse_item(self, element: Any) -> NewsArticle | None:
        """Parse a single HTML element into a :class:`NewsArticle`.

        Args:
            element: A BeautifulSoup Tag (article, body, or card element).

        Returns:
            A :class:`NewsArticle` or ``None`` if parsing fails.
        """
        try:
            return self._build_article(element)
        except Exception as exc:
            _log.debug("Skipping news item: {exc}", exc=exc)
            return None

    def _build_article(self, el: Tag) -> NewsArticle:
        """Extract all fields from the given element."""
        title = self._extract_title(el)
        url = self._extract_url(el)
        author = self._extract_author(el)
        published_at = self._extract_date(el)
        content = self._extract_content(el)
        summary = self._extract_summary(el, content)
        tags = self._extract_tags(el)
        source = self._extract_source(el)

        return NewsArticle(
            title=title,
            url=url,
            source=source,
            author=author,
            published_at=published_at,
            content=content,
            summary=summary,
            tags=tags,
        )

    @staticmethod
    def _extract_title(el: Tag) -> str:
        h1 = el.select_one("h1")
        if h1:
            return h1.get_text(strip=True)
        h2 = el.select_one("h2, .headline, .article-title")
        return h2.get_text(strip=True) if h2 else ""

    @staticmethod
    def _extract_url(el: Tag) -> str:
        canonical = el.select_one("link[rel='canonical']")
        if canonical and canonical.get("href"):
            return str(canonical["href"])
        a = el.select_one("h1 a, h2 a, .headline a")
        return str(a.get("href", "")) if a else ""

    @staticmethod
    def _extract_author(el: Tag) -> str:
        author_el = (
            el.select_one("[rel='author']")
            or el.select_one(".author")
            or el.select_one(".byline")
            or el.select_one("[data-testid='byline']")
        )
        return author_el.get_text(strip=True) if author_el else ""

    @staticmethod
    def _extract_date(el: Tag) -> datetime | None:
        time_el = el.select_one("time[datetime]")
        if time_el:
            dt_str = str(time_el.get("datetime", ""))
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except ValueError:
                pass
        return None

    @staticmethod
    def _extract_content(el: Tag) -> str:
        body_el = (
            el.select_one(".article-body")
            or el.select_one(".article-content")
            or el.select_one("[data-testid='article-body']")
            or el.select_one(".story-body")
            or el.select_one("article")
        )
        if body_el:
            paragraphs = body_el.select("p")
            if paragraphs:
                return " ".join(p.get_text(strip=True) for p in paragraphs)
            return body_el.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_summary(el: Tag, content: str) -> str:
        lead_el = (
            el.select_one(".article-summary")
            or el.select_one(".lead")
            or el.select_one("[data-testid='standfirst']")
            or el.select_one("meta[name='description']")
        )
        if lead_el:
            if lead_el.name == "meta":
                return str(lead_el.get("content", ""))
            return lead_el.get_text(strip=True)
        # Fall back to first 200 chars of content
        return content[:200] if content else ""

    @staticmethod
    def _extract_tags(el: Tag) -> list[str]:
        tag_els = el.select(".tag, .topic, .category, [data-testid='topic-tag']")
        return [t.get_text(strip=True) for t in tag_els[:10] if t.get_text(strip=True)]

    @staticmethod
    def _extract_source(el: Tag) -> str:
        og_site = el.select_one("meta[property='og:site_name']")
        if og_site and og_site.get("content"):
            return str(og_site["content"])
        return ""
