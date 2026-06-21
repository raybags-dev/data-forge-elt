"""Unit tests for concrete crawler models and parsers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from crawlers.base.models import CrawledPage
from crawlers.imdb.models import ImdbTitle
from crawlers.imdb.parser import ImdbParser
from crawlers.news.models import NewsArticle
from crawlers.news.parser import NewsParser
from crawlers.reddit.models import RedditPost
from crawlers.reddit.parser import RedditParser
from crawlers.steam.models import SteamGame
from crawlers.steam.parser import SteamParser

# ── Helpers ───────────────────────────────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _make_page(html: str = "", url: str = "https://example.com") -> CrawledPage:
    return CrawledPage(
        url=url,
        status_code=200,
        html=html,
        text="",
        loaded_at=_utc_now(),
        response_time_ms=100,
    )


# ── Reddit model tests ────────────────────────────────────────────────────────


def test_reddit_models_valid() -> None:
    """RedditPost should validate and store all required fields."""
    post = RedditPost(
        id="t3_abc123",
        title="Hello World",
        author="test_user",
        subreddit="python",
        score=42,
        num_comments=7,
        url="https://old.reddit.com/r/python/comments/abc123",
    )
    assert post.id == "t3_abc123"
    assert post.title == "Hello World"
    assert post.author == "test_user"
    assert post.subreddit == "python"
    assert post.score == 42
    assert post.num_comments == 7
    assert post.text == ""
    assert post.created_utc is None


def test_reddit_post_with_datetime() -> None:
    """RedditPost should accept a datetime for created_utc."""
    now = _utc_now()
    post = RedditPost(
        id="t3_xyz",
        title="Test",
        author="user",
        subreddit="all",
        url="https://reddit.com",
        created_utc=now,
    )
    assert post.created_utc == now


def test_reddit_comment_model() -> None:
    """RedditComment should validate required and optional fields."""
    from crawlers.reddit.models import RedditComment

    comment = RedditComment(
        id="t1_111",
        post_id="t3_abc",
        author="commenter",
        body="Great post!",
        score=10,
        depth=1,
    )
    assert comment.id == "t1_111"
    assert comment.depth == 1


def test_reddit_subreddit_model() -> None:
    """RedditSubreddit should validate and store metadata."""
    from crawlers.reddit.models import RedditSubreddit

    sub = RedditSubreddit(name="python", title="Python", description="All things Python", subscribers=500000)
    assert sub.name == "python"
    assert sub.subscribers == 500000


# ── Steam model tests ─────────────────────────────────────────────────────────


def test_steam_models_valid() -> None:
    """SteamGame should validate and store all expected fields."""
    game = SteamGame(
        app_id="570",
        name="Dota 2",
        description="A popular MOBA game.",
        price="Free to Play",
        release_date="Jul 9, 2013",
        developer="Valve",
        publisher="Valve",
        genres=["Action", "Strategy"],
        rating="Overwhelmingly Positive",
        review_count=1500000,
    )
    assert game.app_id == "570"
    assert game.name == "Dota 2"
    assert "Action" in game.genres
    assert game.review_count == 1500000


def test_steam_game_defaults() -> None:
    """SteamGame optional fields should have sensible defaults."""
    game = SteamGame(app_id="1", name="Test Game")
    assert game.description == ""
    assert game.genres == []
    assert game.review_count == 0


def test_steam_review_model() -> None:
    """SteamReview should validate rating and content fields."""
    from crawlers.steam.models import SteamReview

    review = SteamReview(
        app_id="570",
        author="gamer42",
        rating="Recommended",
        content="10/10 would play again.",
        helpful_votes=100,
    )
    assert review.rating == "Recommended"
    assert review.helpful_votes == 100


# ── IMDB model tests ──────────────────────────────────────────────────────────


def test_imdb_models_valid() -> None:
    """ImdbTitle should validate and store all expected fields."""
    title = ImdbTitle(
        id="tt0111161",
        title="The Shawshank Redemption",
        year="1994",
        rating=9.3,
        votes=2700000,
        genres=["Drama"],
        directors=["Frank Darabont"],
        cast=["Tim Robbins", "Morgan Freeman"],
        runtime_minutes=142,
        plot="Two imprisoned men bond over a number of years.",
    )
    assert title.id == "tt0111161"
    assert title.rating == 9.3
    assert title.votes == 2700000
    assert "Drama" in title.genres


def test_imdb_title_rating_bounds() -> None:
    """ImdbTitle rating must be within [0.0, 10.0]."""
    with pytest.raises(Exception):
        ImdbTitle(id="tt0", title="Test", rating=11.0)

    with pytest.raises(Exception):
        ImdbTitle(id="tt0", title="Test", rating=-1.0)


def test_imdb_rating_model() -> None:
    """ImdbRating should validate rating and votes."""
    from crawlers.imdb.models import ImdbRating

    rating = ImdbRating(title_id="tt0111161", rating=9, votes=1000000)
    assert rating.rating == 9
    assert rating.votes == 1000000


def test_imdb_rating_bounds() -> None:
    """ImdbRating rating must be in [1, 10]."""
    with pytest.raises(Exception):
        from crawlers.imdb.models import ImdbRating

        ImdbRating(title_id="tt0", rating=0)


# ── News model tests ──────────────────────────────────────────────────────────


def test_news_models_valid() -> None:
    """NewsArticle should validate and store all expected fields."""
    now = _utc_now()
    article = NewsArticle(
        title="Breaking News",
        url="https://news.example.com/article/1",
        source="Example News",
        author="Jane Doe",
        published_at=now,
        content="Full article content here.",
        summary="Short summary.",
        tags=["technology", "ai"],
    )
    assert article.title == "Breaking News"
    assert article.source == "Example News"
    assert "technology" in article.tags
    assert article.published_at == now


def test_news_article_optional_fields() -> None:
    """NewsArticle should work with only required fields."""
    article = NewsArticle(title="Minimal Article", url="https://example.com/1")
    assert article.source == ""
    assert article.author == ""
    assert article.published_at is None
    assert article.tags == []


# ── Parser tests — empty/minimal HTML ────────────────────────────────────────


def test_reddit_parser_returns_list_on_empty_html() -> None:
    """RedditParser.parse_page() must return [] on empty HTML, never raise."""
    parser = RedditParser()
    page = _make_page(html="")
    result = parser.parse_page(page)
    assert isinstance(result, list)
    assert result == []


def test_reddit_parser_returns_list_on_minimal_html() -> None:
    """RedditParser.parse_page() must handle minimal HTML gracefully."""
    parser = RedditParser()
    page = _make_page(html="<html><body><p>Nothing here</p></body></html>")
    result = parser.parse_page(page)
    assert isinstance(result, list)


def test_steam_parser_returns_list_on_empty_html() -> None:
    """SteamParser.parse_page() must return [] on empty HTML, never raise."""
    parser = SteamParser()
    page = _make_page(html="")
    result = parser.parse_page(page)
    assert isinstance(result, list)
    assert result == []


def test_steam_parser_returns_list_on_minimal_html() -> None:
    """SteamParser.parse_page() must handle minimal HTML gracefully."""
    parser = SteamParser()
    page = _make_page(html="<html><body><div>No games here</div></body></html>")
    result = parser.parse_page(page)
    assert isinstance(result, list)


def test_imdb_parser_returns_list_on_empty_html() -> None:
    """ImdbParser.parse_page() must return [] on empty HTML, never raise."""
    parser = ImdbParser()
    page = _make_page(html="")
    result = parser.parse_page(page)
    assert isinstance(result, list)
    assert result == []


def test_news_parser_returns_list_on_empty_html() -> None:
    """NewsParser.parse_page() must return [] on empty HTML, never raise."""
    parser = NewsParser()
    page = _make_page(html="")
    result = parser.parse_page(page)
    assert isinstance(result, list)
    assert result == []


def test_reddit_parser_with_realistic_html() -> None:
    """RedditParser should extract posts from old Reddit HTML."""
    html = """
    <html><body>
    <div id="siteTable">
      <div class="thing link" data-fullname="t3_abc123" data-subreddit="python"
           data-author="testuser" data-score="42">
        <p class="title"><a class="title may-blank" href="/r/python/comments/abc123/test">
          Test Post Title
        </a></p>
        <a class="comments" href="/r/python/comments/abc123/test">15 comments</a>
        <time class="live-timestamp" datetime="2024-01-15T12:00:00+00:00">just now</time>
      </div>
    </div>
    </body></html>
    """
    parser = RedditParser()
    page = _make_page(html=html, url="https://old.reddit.com/r/python")
    results = parser.parse_page(page)
    assert isinstance(results, list)
    if results:
        assert results[0].title == "Test Post Title"
        assert results[0].subreddit == "python"


def test_imdb_parser_with_classic_chart_html() -> None:
    """ImdbParser should extract titles from classic top-250 table rows."""
    html = """
    <html><body>
    <table>
    <tr>
      <td class="titleColumn">
        1. <a href="/title/tt0111161/?pf_rd_m=A2FGELUUNOQJNL">
          The Shawshank Redemption
        </a>
        <span class="secondaryInfo">(1994)</span>
      </td>
      <td class="ratingColumn imdbRating">
        <strong title="9.3 based on 2,700,000 user ratings">9.3</strong>
      </td>
    </tr>
    </table>
    </body></html>
    """
    parser = ImdbParser()
    page = _make_page(html=html, url="https://www.imdb.com/chart/top")
    results = parser.parse_page(page)
    assert isinstance(results, list)
    if results:
        assert results[0].id == "tt0111161"
        assert results[0].rating == pytest.approx(9.3)
