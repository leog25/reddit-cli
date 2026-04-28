"""Tests for browse expansion commands."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from reddit_cli.models import Listing, Post

runner = CliRunner()


def make_post(**overrides) -> Post:
    defaults = dict(
        id="abc123", title="Test", author="user", subreddit="python",
        score=42, upvote_ratio=0.95, num_comments=10, created_utc=1774168543.0,
        permalink="/r/python/comments/abc123/test/",
        url="https://www.reddit.com/r/python/comments/abc123/test/",
        selftext="", is_self=True,
    )
    defaults.update(overrides)
    return Post(**defaults)


def make_listing(n=2):
    posts = [make_post(id=f"p{i}", title=f"Post {i}") for i in range(n)]
    return Listing(posts=posts, after="cursor" if n > 0 else None, count=n)


class TestPopular:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        MockClient.return_value.get_popular.return_value = make_listing()
        result = runner.invoke(app, ["popular", "--limit", "2"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert len(data["data"]["posts"]) == 2


class TestAll:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        MockClient.return_value.get_all.return_value = make_listing()
        result = runner.invoke(app, ["all", "--limit", "2"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True


class TestFeed:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        MockClient.return_value.get_home.return_value = make_listing()
        result = runner.invoke(app, ["feed", "--limit", "2"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True


class TestUserPosts:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        MockClient.return_value.get_user_posts.return_value = make_listing()
        result = runner.invoke(app, ["user", "posts", "spez", "--limit", "2"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True


class TestUserComments:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        # get_user_comments returns raw dict
        MockClient.return_value.get_user_comments.return_value = {
            "kind": "Listing",
            "data": {"children": [], "after": None},
        }
        result = runner.invoke(app, ["user", "comments", "spez", "--limit", "2"])
        assert result.exit_code == 0


class TestOpen:
    @patch("reddit_cli.commands.browse.open_url")
    def test_open_by_url(self, mock_open):
        from reddit_cli.main import app

        result = runner.invoke(app, ["open", "https://reddit.com/r/python"])
        assert result.exit_code == 0
        mock_open.assert_called_once()
