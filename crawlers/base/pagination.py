"""Pagination strategies for the DataForge crawler engine.

Each strategy encapsulates a single algorithm for generating the URL of the
next page given the current URL and HTML body.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup


class PaginationStrategy(ABC):
    """Abstract base class for URL pagination strategies."""

    @abstractmethod
    def next_url(
        self, current_url: str, page_html: str, current_page: int
    ) -> str | None:
        """Return the URL of the next page, or ``None`` when exhausted.

        Args:
            current_url: The URL that was just fetched.
            page_html: The HTML body of the current page.
            current_page: 1-based index of the page just fetched.
        """


class NoPagination(PaginationStrategy):
    """Strategy for single-page sources — always signals completion."""

    def next_url(
        self, current_url: str, page_html: str, current_page: int
    ) -> str | None:
        """Always return ``None`` to indicate no further pages exist.

        Args:
            current_url: Unused.
            page_html: Unused.
            current_page: Unused.
        """
        return None


class PageNumberStrategy(PaginationStrategy):
    """Appends or increments a ``?page=N`` query parameter.

    Args:
        max_pages: Stop after this many pages (inclusive).
        param_name: Query-string parameter name (default ``"page"``).
    """

    def __init__(self, max_pages: int, param_name: str = "page") -> None:
        """Initialise the strategy.

        Args:
            max_pages: Maximum page index to crawl (1-based).
            param_name: Name of the page query parameter.
        """
        self.max_pages: int = max_pages
        self.param_name: str = param_name

    def next_url(
        self, current_url: str, page_html: str, current_page: int
    ) -> str | None:
        """Build the URL for page ``current_page + 1``.

        Returns ``None`` when ``current_page >= max_pages``.

        Args:
            current_url: Base URL whose query string will be modified.
            page_html: Unused.
            current_page: The page just fetched (1-based).
        """
        next_page = current_page + 1
        if next_page > self.max_pages:
            return None

        parsed = urlparse(current_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params[self.param_name] = [str(next_page)]

        flat_params = {k: v[0] for k, v in params.items()}
        new_query = urlencode(flat_params)
        new_parsed = parsed._replace(query=new_query)
        return urlunparse(new_parsed)


class CursorStrategy(PaginationStrategy):
    """Extracts a next-page cursor from HTML and appends it to the base URL.

    Args:
        cursor_selector: CSS selector that identifies the element carrying
            the cursor value (in its text or ``href`` attribute).
        cursor_param: Query-string parameter name for the cursor.
        attr: Attribute to read from the matched element.  Use ``"text"`` to
            read the element's text content.
    """

    def __init__(
        self,
        cursor_selector: str,
        cursor_param: str = "cursor",
        attr: str = "data-cursor",
    ) -> None:
        """Initialise the cursor strategy.

        Args:
            cursor_selector: BeautifulSoup CSS selector for the cursor element.
            cursor_param: Query-string parameter name.
            attr: Element attribute containing the cursor value, or ``"text"``.
        """
        self.cursor_selector: str = cursor_selector
        self.cursor_param: str = cursor_param
        self.attr: str = attr

    def _extract_cursor(self, page_html: str) -> str | None:
        """Parse *page_html* and return the cursor value, or ``None``."""
        soup = BeautifulSoup(page_html, "html.parser")
        element = soup.select_one(self.cursor_selector)
        if element is None:
            return None
        if self.attr == "text":
            return element.get_text(strip=True) or None
        value = element.get(self.attr)
        return str(value) if value else None

    def next_url(
        self, current_url: str, page_html: str, current_page: int
    ) -> str | None:
        """Build the next URL using the cursor extracted from *page_html*.

        Returns ``None`` if no cursor element is found.

        Args:
            current_url: Base URL to append the cursor parameter to.
            page_html: HTML of the current page.
            current_page: Unused — cursors are stateless.
        """
        cursor = self._extract_cursor(page_html)
        if cursor is None:
            return None

        parsed = urlparse(current_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params[self.cursor_param] = [cursor]

        flat_params = {k: v[0] for k, v in params.items()}
        new_query = urlencode(flat_params)
        new_parsed = parsed._replace(query=new_query)
        return urlunparse(new_parsed)
