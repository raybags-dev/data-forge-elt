"""HTML parser for IMDB pages.

Targets IMDB's chart/list pages (e.g. Top 250, Most Popular) as well as
individual title pages.  Uses BeautifulSoup with stable CSS selectors.
"""

from __future__ import annotations

import contextlib
import re

from bs4 import BeautifulSoup, Tag

from crawlers.base.models import CrawledPage
from crawlers.imdb.models import ImdbTitle
from shared.logger import get_logger

_log = get_logger(__name__)
_PARSERS = ["lxml", "html.parser"]
_VOTES_RE = re.compile(r"[\d,]+")


def _make_soup(html: str) -> BeautifulSoup:
    for parser in _PARSERS:
        try:
            return BeautifulSoup(html, parser)
        except Exception:
            continue
    return BeautifulSoup(html, "html.parser")


class ImdbParser:
    """Parses IMDB HTML into :class:`ImdbTitle` records.

    Supports both chart listing pages and individual title detail pages.
    """

    def parse_page(self, page: CrawledPage) -> list[ImdbTitle]:
        """Extract title records from *page*.

        Args:
            page: Fetched page snapshot.

        Returns:
            List of :class:`ImdbTitle` objects (may be empty).
        """
        try:
            soup = _make_soup(page.html)
            return self._detect_and_parse(soup, page.url)
        except Exception as exc:
            _log.warning("ImdbParser failed on {url}: {exc}", url=page.url, exc=exc)
            return []

    def _detect_and_parse(
        self, soup: BeautifulSoup, url: str
    ) -> list[ImdbTitle]:
        """Detect page type and dispatch to the appropriate parser."""
        # Chart page: rows in a list table
        chart_rows = soup.select(".lister-list .lister-item, .ipc-metadata-list-summary-item")
        if chart_rows:
            return self._parse_chart(chart_rows)

        # Classic top-250 table
        classic_rows = soup.select(".titleColumn")
        if classic_rows:
            return self._parse_classic_chart(soup)

        # Individual title page
        if soup.select_one("[data-testid='hero-title-block__title']") or soup.select_one("h1.TitleHeader__TitleText"):
            title = self._parse_title_page(soup, url)
            return [title] if title else []

        return []

    def _parse_classic_chart(self, soup: BeautifulSoup) -> list[ImdbTitle]:
        """Parse the classic IMDB Top-250 table layout."""
        rows = soup.select("tr")
        titles: list[ImdbTitle] = []
        for row in rows:
            title = self.parse_item(row)
            if title:
                titles.append(title)
        return titles

    def _parse_chart(self, elements: list[Tag]) -> list[ImdbTitle]:
        """Parse modern IMDB chart/list elements."""
        titles: list[ImdbTitle] = []
        for el in elements:
            title = self.parse_item(el)
            if title:
                titles.append(title)
        return titles

    def parse_item(self, element: Tag) -> ImdbTitle | None:
        """Parse a single chart row or list item into an :class:`ImdbTitle`.

        Args:
            element: BeautifulSoup Tag for a single list entry.

        Returns:
            An :class:`ImdbTitle` or ``None`` if parsing fails.
        """
        try:
            return self._build_from_row(element)
        except Exception as exc:
            _log.debug("Skipping IMDB item: {exc}", exc=exc)
            return None

    def _build_from_row(self, el: Tag) -> ImdbTitle:
        """Extract fields from a chart row element."""
        link = (
            el.select_one(".titleColumn a")
            or el.select_one("a[href*='/title/tt']")
        )

        title_id = ""
        title_text = ""
        year = ""

        if link:
            href = str(link.get("href", ""))
            match = re.search(r"/title/(tt\d+)", href)
            if match:
                title_id = match.group(1)
            title_text = link.get_text(strip=True)

        year_span = (
            el.select_one(".titleColumn .secondaryInfo")
            or el.select_one(".cli-title-metadata-item")
        )
        if year_span:
            year = year_span.get_text(strip=True).strip("()")

        rating_el = el.select_one(".imdbRating strong, .ipc-rating-star--rating")
        rating = 0.0
        if rating_el:
            with contextlib.suppress(ValueError):
                rating = float(rating_el.get_text(strip=True))

        votes_el = el.select_one(".imdbRating strong[title]")
        votes = 0
        if votes_el:
            title_attr = str(votes_el.get("title", ""))
            m = _VOTES_RE.search(title_attr)
            if m:
                votes = int(m.group().replace(",", ""))

        return ImdbTitle(
            id=title_id or "unknown",
            title=title_text,
            year=year,
            rating=rating,
            votes=votes,
        )

    def _parse_title_page(
        self, soup: BeautifulSoup, url: str
    ) -> ImdbTitle | None:
        """Parse an individual IMDB title detail page."""
        try:
            return self._build_from_title_page(soup, url)
        except Exception as exc:
            _log.debug("Failed to parse IMDB title page: {exc}", exc=exc)
            return None

    def _build_from_title_page(
        self, soup: BeautifulSoup, url: str
    ) -> ImdbTitle:
        """Extract rich metadata from a title detail page."""
        match = re.search(r"/title/(tt\d+)", url)
        title_id = match.group(1) if match else "unknown"

        title_el = (
            soup.select_one("[data-testid='hero-title-block__title']")
            or soup.select_one("h1")
        )
        title = title_el.get_text(strip=True) if title_el else ""

        year_el = soup.select_one("[data-testid='hero-title-block__metadata'] a")
        year = year_el.get_text(strip=True) if year_el else ""

        rating_el = soup.select_one("[data-testid='hero-rating-bar__aggregate-rating__score'] span")
        rating = 0.0
        if rating_el:
            with contextlib.suppress(ValueError):
                rating = float(rating_el.get_text(strip=True))

        plot_el = soup.select_one("[data-testid='plot']")
        plot = plot_el.get_text(strip=True) if plot_el else ""

        genre_els = soup.select("[data-testid='genres'] a, .ipc-chip__text")
        genres = [g.get_text(strip=True) for g in genre_els[:5]]

        return ImdbTitle(
            id=title_id,
            title=title,
            year=year,
            rating=rating,
            genres=genres,
            plot=plot,
        )
