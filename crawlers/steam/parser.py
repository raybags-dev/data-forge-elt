"""HTML parser for Steam store pages.

Targets Steam's standard store page layout, extracting game metadata from
elements such as ``#appHubAppName``, ``.game_description_snippet``, and
``.responsive_reviewdesc``.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from crawlers.base.models import CrawledPage
from crawlers.steam.models import SteamGame
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


class SteamParser:
    """Parses Steam store HTML into :class:`SteamGame` records.

    Handles both individual app pages and search-result listing pages.
    """

    def parse_page(self, page: CrawledPage) -> list[SteamGame]:
        """Extract game records from *page*.

        Args:
            page: Fetched page snapshot.

        Returns:
            List of :class:`SteamGame` objects (may be empty).
        """
        try:
            soup = _make_soup(page.html)
            return self._detect_and_parse(soup, page.url)
        except Exception as exc:
            _log.warning("SteamParser failed on {url}: {exc}", url=page.url, exc=exc)
            return []

    def _detect_and_parse(
        self, soup: BeautifulSoup, url: str
    ) -> list[SteamGame]:
        """Detect page type (app or search) and delegate accordingly."""
        if soup.select_one("#appHubAppName") or soup.select_one(".apphub_AppName"):
            game = self._parse_app_page(soup, url)
            return [game] if game else []
        return self._parse_search_results(soup)

    def _parse_app_page(
        self, soup: BeautifulSoup, url: str
    ) -> SteamGame | None:
        """Parse a single Steam app page."""
        try:
            return self._build_from_app_page(soup, url)
        except Exception as exc:
            _log.debug("Skipping Steam app page: {exc}", exc=exc)
            return None

    def _build_from_app_page(
        self, soup: BeautifulSoup, url: str
    ) -> SteamGame:
        """Extract fields from a Steam app detail page."""
        app_id = self._extract_app_id(url)

        name_el = soup.select_one("#appHubAppName") or soup.select_one(".apphub_AppName")
        name = name_el.get_text(strip=True) if name_el else ""

        desc_el = soup.select_one(".game_description_snippet")
        description = desc_el.get_text(strip=True) if desc_el else ""

        price_el = soup.select_one(".game_purchase_price") or soup.select_one(".discount_final_price")
        price = price_el.get_text(strip=True) if price_el else ""

        date_el = soup.select_one(".date")
        release_date = date_el.get_text(strip=True) if date_el else ""

        dev_el = soup.select_one("#developers_list") or soup.select_one(".dev_row a")
        developer = dev_el.get_text(strip=True) if dev_el else ""

        genre_els = soup.select("#genresAndManufacturer a, .details_block a")
        genres = [g.get_text(strip=True) for g in genre_els[:5]]

        rating_el = soup.select_one(".responsive_reviewdesc") or soup.select_one(".game_review_summary")
        rating = rating_el.get_text(strip=True) if rating_el else ""

        return SteamGame(
            app_id=app_id,
            name=name,
            description=description,
            price=price,
            release_date=release_date,
            developer=developer,
            genres=genres,
            rating=rating,
        )

    def _parse_search_results(self, soup: BeautifulSoup) -> list[SteamGame]:
        """Parse Steam search result rows."""
        rows = soup.select("#search_resultsRows .search_result_row, .search_result_row")
        games: list[SteamGame] = []
        for row in rows:
            game = self.parse_item(row)
            if game:
                games.append(game)
        return games

    def parse_item(self, element: Tag) -> SteamGame | None:
        """Parse a single search-result element.

        Args:
            element: A BeautifulSoup Tag for a search result row.

        Returns:
            A :class:`SteamGame` or ``None`` if parsing fails.
        """
        try:
            return self._build_from_search_row(element)
        except Exception as exc:
            _log.debug("Skipping Steam search row: {exc}", exc=exc)
            return None

    def _build_from_search_row(self, el: Tag) -> SteamGame:
        """Extract fields from a search result row."""
        href = el.get("href", "")
        app_id = self._extract_app_id(str(href))

        title_el = el.select_one(".title")
        name = title_el.get_text(strip=True) if title_el else ""

        price_el = el.select_one(".search_price .discount_final_price") or el.select_one(".search_price")
        price = price_el.get_text(strip=True) if price_el else ""

        date_el = el.select_one(".search_released")
        release_date = date_el.get_text(strip=True) if date_el else ""

        rating_el = el.select_one(".search_review_summary")
        rating = ""
        if rating_el:
            rating = str(rating_el.get("data-tooltip-html", "")).split("<br>")[0]

        return SteamGame(
            app_id=app_id,
            name=name,
            price=price,
            release_date=release_date,
            rating=rating,
        )

    @staticmethod
    def _extract_app_id(url: str) -> str:
        """Extract the Steam app ID from a store URL."""
        parts = url.rstrip("/").split("/")
        for i, part in enumerate(parts):
            if part == "app" and i + 1 < len(parts):
                return parts[i + 1]
        return ""
