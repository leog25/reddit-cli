"""Tests for output routing v2: schema_version, string codes, YAML, compact."""

import json

from reddit_cli.models import Listing, Post


def make_post(**overrides) -> Post:
    defaults = dict(
        id="abc123", title="Test Post", author="testuser", subreddit="python",
        score=42, upvote_ratio=0.95, num_comments=10, created_utc=1774168543.0,
        permalink="/r/python/comments/abc123/test_post/",
        url="https://www.reddit.com/r/python/comments/abc123/test_post/",
        selftext="Hello world", is_self=True,
    )
    defaults.update(overrides)
    return Post(**defaults)


def make_listing(n: int = 3) -> Listing:
    posts = [make_post(id=f"post{i}", title=f"Post {i}", score=i * 10) for i in range(n)]
    return Listing(posts=posts, after="cursor" if n > 0 else None, count=n)


class TestSchemaVersion:
    def test_success_has_schema_version(self, capsys):
        from reddit_cli.output import output_json

        output_json(make_post())
        data = json.loads(capsys.readouterr().out)
        assert data["schema_version"] == "1"
        assert data["ok"] is True

    def test_error_has_schema_version(self, capsys):
        from reddit_cli.output import output_error

        output_error("not_found", "Not found")
        data = json.loads(capsys.readouterr().out)
        assert data["schema_version"] == "1"
        assert data["ok"] is False

    def test_error_uses_string_code(self, capsys):
        from reddit_cli.output import output_error

        output_error("rate_limited", "Too many requests")
        data = json.loads(capsys.readouterr().out)
        assert data["error"]["code"] == "rate_limited"


class TestYamlOutput:
    def test_yaml_output_valid(self, capsys):
        from reddit_cli.output import output_yaml

        output_yaml(make_post())
        text = capsys.readouterr().out
        import yaml
        parsed = yaml.safe_load(text)
        assert parsed["ok"] is True
        assert parsed["schema_version"] == "1"
        assert parsed["data"]["id"] == "abc123"

    def test_yaml_listing(self, capsys):
        from reddit_cli.output import output_yaml

        output_yaml(make_listing(2))
        text = capsys.readouterr().out
        import yaml
        parsed = yaml.safe_load(text)
        assert len(parsed["data"]["posts"]) == 2


class TestCompactOutput:
    def test_compact_strips_fields(self, capsys):
        from reddit_cli.output import output_json

        listing = make_listing(1)
        output_json(listing, compact=True)
        data = json.loads(capsys.readouterr().out)
        post = data["data"]["posts"][0]
        # Compact should keep essential fields
        assert "id" in post
        assert "title" in post
        assert "score" in post
        assert "author" in post
        assert "permalink" in post
        # Compact should strip non-essential fields
        assert "selftext" not in post
        assert "domain" not in post
        assert "spoiler" not in post


class TestResolveOutputFormat:
    def test_explicit_json(self):
        from reddit_cli.output import resolve_output_format

        assert resolve_output_format(as_json=True, as_yaml=False) == "json"

    def test_explicit_yaml(self):
        from reddit_cli.output import resolve_output_format

        assert resolve_output_format(as_json=False, as_yaml=True) == "yaml"

    def test_env_override(self, monkeypatch):
        from reddit_cli.output import resolve_output_format

        monkeypatch.setenv("OUTPUT", "yaml")
        assert resolve_output_format(as_json=False, as_yaml=False) == "yaml"

    def test_default_none(self, monkeypatch):
        from reddit_cli.output import resolve_output_format

        monkeypatch.delenv("OUTPUT", raising=False)
        assert resolve_output_format(as_json=False, as_yaml=False) is None


class TestFormatHelpers:
    def test_format_score_small(self):
        from reddit_cli.output import format_score

        assert format_score(42) == "42"

    def test_format_score_thousands(self):
        from reddit_cli.output import format_score

        assert format_score(1500) == "1.5k"

    def test_format_score_exact_thousand(self):
        from reddit_cli.output import format_score

        assert format_score(1000) == "1.0k"

    def test_format_time_recent(self):
        import time

        from reddit_cli.output import format_time

        result = format_time(time.time() - 300)  # 5 min ago
        assert "m" in result or "min" in result

    def test_format_time_old(self):
        from reddit_cli.output import format_time

        result = format_time(1118030400.0)  # 2005
        assert "2005" in result
