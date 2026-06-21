"""Pydantic models for the News crawler."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """A single news article extracted from a news website.

    Attributes:
        title: Article headline.
        url: Canonical URL of the article.
        source: Publication name (e.g. ``"BBC News"``).
        author: Byline author name(s).
        published_at: UTC datetime when the article was published.
        content: Full article body text.
        summary: Short summary or lead paragraph.
        tags: Topic tags or category labels.
    """

    title: str
    url: str
    source: str = ""
    author: str = ""
    published_at: datetime | None = None
    content: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
