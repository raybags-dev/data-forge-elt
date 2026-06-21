"""Pydantic models for Steam crawler data."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SteamGame(BaseModel):
    """Metadata for a Steam game or application.

    Attributes:
        app_id: Numeric Steam application identifier.
        name: Game title.
        description: Short marketing description snippet.
        price: Display price string (e.g. ``"$29.99"`` or ``"Free to Play"``).
        release_date: Release date string as shown on Steam.
        developer: Developer name(s).
        publisher: Publisher name(s).
        genres: List of genre labels.
        rating: Overall review rating label (e.g. ``"Very Positive"``).
        review_count: Total number of user reviews.
    """

    app_id: str
    name: str
    description: str = ""
    price: str = ""
    release_date: str = ""
    developer: str = ""
    publisher: str = ""
    genres: list[str] = Field(default_factory=list)
    rating: str = ""
    review_count: int = Field(default=0, ge=0)


class SteamReview(BaseModel):
    """A single Steam user review.

    Attributes:
        app_id: Steam application this review belongs to.
        author: Steam username of the reviewer.
        rating: ``"Recommended"`` or ``"Not Recommended"``.
        content: Full review text.
        helpful_votes: Number of users who found this review helpful.
        created_at: UTC timestamp when the review was posted.
    """

    app_id: str
    author: str
    rating: str
    content: str = ""
    helpful_votes: int = Field(default=0, ge=0)
    created_at: datetime | None = None
