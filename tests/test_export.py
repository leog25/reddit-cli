"""Tests for export command."""

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


def make_listing(n=3):
    posts = [make_post(id=f"p{i}", title=f"Post {i}", score=i * 10) for i in range(n)]
    return Listing(posts=posts, after=None, count=n)


class TestExportJSON:
    @patch("reddit_cli.client.RedditClient")
    def test_export_json(self, MockClient, tmp_path):
        from reddit_cli.main import app

        MockClient.return_value.search.return_value = make_listing(2)
        outfile = str(tmp_path / "out.json")

        result = runner.invoke(app, [
            "export", "python", "--format", "json", "--output", outfile, "--count", "2"
        ])
        assert result.exit_code == 0

        with open(outfile) as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["title"] == "Post 0"


class TestExportCSV:
    @patch("reddit_cli.client.RedditClient")
    def test_export_csv(self, MockClient, tmp_path):
        from reddit_cli.main import app

        MockClient.return_value.search.return_value = make_listing(2)
        outfile = str(tmp_path / "out.csv")

        result = runner.invoke(app, [
            "export", "python", "--format", "csv", "--output", outfile, "--count", "2"
        ])
        assert result.exit_code == 0

        with open(outfile) as f:
            lines = f.readlines()
        assert len(lines) == 3  # header + 2 rows
        assert "title" in lines[0].lower()
