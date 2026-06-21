"""Pydantic models for Reddit crawler data.

Models represent the data extracted from Reddit's old-style HTML interface.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RedditPost(BaseModel):
    """A single Reddit submission (link or self-post).

    Attributes:
        id: Reddit post ID (e.g. ``t3_abc123``).
        title: Post title text.
        author: Username of the post author.
        subreddit: Subreddit name without the ``r/`` prefix.
        score: Net upvote score.
        num_comments: Total comment count.
        url: Post permalink URL.
        created_utc: UTC timestamp of post creation.
        text: Self-post body text, if any.
    """

    id: str
    title: str
    author: str
    subreddit: str
    score: int = 0
    num_comments: int = 0
    url: str
    created_utc: datetime | None = None
    text: str = ""


class RedditComment(BaseModel):
    """A single Reddit comment.

    Attributes:
        id: Reddit comment ID (e.g. ``t1_xyz789``).
        post_id: ID of the parent post.
        author: Username of the comment author.
        body: Comment text content.
        score: Net upvote score.
        created_utc: UTC timestamp of comment creation.
        depth: Nesting depth (0 = top-level).
    """

    id: str
    post_id: str
    author: str
    body: str
    score: int = 0
    created_utc: datetime | None = None
    depth: int = 0


class RedditSubreddit(BaseModel):
    """Metadata for a Reddit community.

    Attributes:
        name: Subreddit name without the ``r/`` prefix.
        title: Display title of the subreddit.
        description: Public description text.
        subscribers: Subscriber count.
    """

    name: str
    title: str = ""
    description: str = ""
    subscribers: int = Field(default=0, ge=0)
