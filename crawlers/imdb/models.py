"""Pydantic models for IMDB crawler data."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImdbTitle(BaseModel):
    """Metadata for an IMDB title (film, series, etc.).

    Attributes:
        id: IMDB title ID (e.g. ``tt0111161``).
        title: Display title.
        year: Release year string (may include ranges like ``2020–2023``).
        rating: IMDb user rating (0.0–10.0).
        votes: Number of user votes.
        genres: List of genre strings.
        directors: List of director names.
        cast: List of top-billed cast member names.
        runtime_minutes: Runtime in minutes.
        plot: Short plot synopsis.
    """

    id: str
    title: str
    year: str = ""
    rating: float = Field(default=0.0, ge=0.0, le=10.0)
    votes: int = Field(default=0, ge=0)
    genres: list[str] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)
    cast: list[str] = Field(default_factory=list)
    runtime_minutes: int = Field(default=0, ge=0)
    plot: str = ""


class ImdbRating(BaseModel):
    """A single user rating entry for an IMDB title.

    Attributes:
        title_id: IMDB title this rating belongs to.
        rating: User-submitted rating (1–10).
        votes: Total votes at this rating level.
    """

    title_id: str
    rating: int = Field(ge=1, le=10)
    votes: int = Field(default=0, ge=0)
