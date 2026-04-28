"""Tests for the ``reddit exec`` command."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from reddit_cli.models import Listing, Post

runner = CliRunner()

_decoder = json.JSONDecoder()


def parse_json(output: str) -> dict:
    """Parse the first JSON object from output (ignoring stderr mixed in)."""
    return _decoder.raw_decode(output)[0]


def make_post(**overrides) -> Post:
    defaults = dict(
        id="abc123",
        title="Test Post",
        author="testuser",
        subreddit="python",
        score=42,
        upvote_ratio=0.95,
        num_comments=10,
        created_utc=1700000000.0,
        permalink="/r/python/comments/abc123/test/",
        url="https://reddit.com/r/python/comments/abc123/test/",
        selftext="body",
        domain="self.python",
        is_self=True,
        over_18=False,
        spoiler=False,
        stickied=False,
        locked=False,
        is_video=False,
    )
    defaults.update(overrides)
    return Post(**defaults)


def make_listing(n: int = 1) -> Listing:
    posts = [make_post(id=f"post{i}", title=f"Post {i}") for i in range(n)]
    return Listing(posts=posts, after=None, count=n)


# ── Input modes ──────────────────────────────────────────────────────────


class TestInputModes:
    @patch("reddit_cli.client.RedditClient")
    def test_exec_inline_code(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-c", "result.append({'x': 1})"])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"] == [{"x": 1}]

    @patch("reddit_cli.client.RedditClient")
    def test_exec_file(self, MockClient, tmp_path):
        from reddit_cli.main import app

        script = tmp_path / "test.py"
        script.write_text("result.append({'hello': 'world'})")
        result = runner.invoke(app, ["exec", str(script)])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["data"] == [{"hello": "world"}]

    @patch("reddit_cli.client.RedditClient")
    def test_exec_stdin(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-"], input="result.append(42)")
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["data"] == [42]

    @patch("reddit_cli.client.RedditClient")
    def test_exec_no_input_error(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec"])
        assert result.exit_code == 2
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "usage"

    @patch("reddit_cli.client.RedditClient")
    def test_exec_file_not_found(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "nonexistent_xyz.py"])
        assert result.exit_code == 1
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "file_not_found"


# ── Namespace availability ───────────────────────────────────────────────


class TestNamespace:
    @patch("reddit_cli.client.RedditClient")
    def test_client_available(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value.__enter__.return_value
        instance.get_popular.return_value = make_listing(1)

        code = (
            "listing = client.get_popular(limit=1)\n"
            "result.append(len(listing.posts))"
        )
        result = runner.invoke(app, ["exec", "-c", code])
        assert result.exit_code == 0
        instance.get_popular.assert_called_once_with(limit=1)
        data = parse_json(result.output)
        assert data["data"] == [1]

    @patch("reddit_cli.client.RedditClient")
    def test_models_available(self, MockClient):
        from reddit_cli.main import app

        code = "result.append(Post.__name__); result.append(Comment.__name__)"
        result = runner.invoke(app, ["exec", "-c", code])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["data"] == ["Post", "Comment"]

    @patch("reddit_cli.client.RedditClient")
    def test_sleep_available(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-c", "sleep(0)"])
        assert result.exit_code == 0

    @patch("reddit_cli.client.RedditClient")
    def test_result_accumulator(self, MockClient):
        from reddit_cli.main import app

        code = "result.append(1); result.append(2); result.append(3)"
        result = runner.invoke(app, ["exec", "-c", code])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["data"] == [1, 2, 3]


# ── Output format ────────────────────────────────────────────────────────


class TestOutput:
    @patch("reddit_cli.client.RedditClient")
    def test_output_envelope_structure(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-c", "result.append(1)"])
        data = parse_json(result.output)
        assert set(data.keys()) == {"ok", "schema_version", "data"}
        assert data["ok"] is True
        assert data["schema_version"] == "1"

    @patch("reddit_cli.client.RedditClient")
    def test_pydantic_model_serialized(self, MockClient):
        from reddit_cli.main import app

        code = (
            "p = Post(id='x', title='T', author='a', subreddit='s', score=1,"
            " upvote_ratio=0.5, num_comments=0, created_utc=0.0,"
            " permalink='', url='', is_self=True, over_18=False,"
            " spoiler=False, stickied=False, locked=False, is_video=False)\n"
            "result.append(p)"
        )
        result = runner.invoke(app, ["exec", "-c", code])
        assert result.exit_code == 0
        data = parse_json(result.output)
        item = data["data"][0]
        assert isinstance(item, dict)
        assert item["id"] == "x"
        assert item["title"] == "T"

    @patch("reddit_cli.client.RedditClient")
    def test_empty_result(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-c", "pass"])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["data"] == []


# ── Error handling ───────────────────────────────────────────────────────


class TestErrors:
    @patch("reddit_cli.client.RedditClient")
    def test_script_error_envelope(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-c", "raise ValueError('boom')"])
        assert result.exit_code == 1
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "script_error"
        assert "boom" in data["error"]["message"]

    @patch("reddit_cli.client.RedditClient")
    def test_syntax_error(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-c", "def (invalid"])
        assert result.exit_code == 1
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "script_error"

    @patch("reddit_cli.client.RedditClient")
    def test_traceback_in_detail(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-c", "raise ValueError('boom')"])
        data = parse_json(result.output)
        assert "Traceback" in data["error"]["detail"]


# ── Timeout ──────────────────────────────────────────────────────────────


class TestTimeout:
    @patch("reddit_cli.client.RedditClient")
    def test_timeout_error(self, MockClient):
        from reddit_cli.main import app

        code = "import time; time.sleep(999)"
        result = runner.invoke(app, ["exec", "-c", code, "--timeout", "1"])
        assert result.exit_code == 1
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "timeout"


# ── Cleanup and edge cases ───────────────────────────────────────────────


class TestCleanup:
    @patch("reddit_cli.client.RedditClient")
    def test_client_cleanup_on_error(self, MockClient):
        from reddit_cli.main import app

        runner.invoke(app, ["exec", "-c", "raise RuntimeError('fail')"])
        MockClient.return_value.__exit__.assert_called()

    @patch("reddit_cli.client.RedditClient")
    def test_mixed_result_types(self, MockClient):
        from reddit_cli.main import app

        code = (
            "result.append({'plain': True})\n"
            "p = Post(id='x', title='T', author='a', subreddit='s', score=1,"
            " upvote_ratio=0.5, num_comments=0, created_utc=0.0,"
            " permalink='', url='', is_self=True, over_18=False,"
            " spoiler=False, stickied=False, locked=False, is_video=False)\n"
            "result.append(p)"
        )
        result = runner.invoke(app, ["exec", "-c", code])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["data"][0] == {"plain": True}
        assert data["data"][1]["id"] == "x"

    @patch("reddit_cli.client.RedditClient")
    def test_print_does_not_corrupt_json(self, MockClient):
        from reddit_cli.main import app

        code = "print('hello'); result.append({'after_print': True})"
        result = runner.invoke(app, ["exec", "-c", code])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"] == [{"after_print": True}]

    @patch("reddit_cli.client.RedditClient")
    def test_sys_exit_zero_is_success(self, MockClient):
        from reddit_cli.main import app

        code = "result.append(1); import sys; sys.exit(0)"
        result = runner.invoke(app, ["exec", "-c", code])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"] == [1]

    @patch("reddit_cli.client.RedditClient")
    def test_sys_exit_nonzero_is_error(self, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["exec", "-c", "import sys; sys.exit(1)"])
        assert result.exit_code == 1
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "script_error"
