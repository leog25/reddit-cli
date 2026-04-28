"""Tests for OutputContext, emit(), and exit_for_error()."""

import json
from io import StringIO
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from reddit_cli.errors import NotFoundError, RedditAPIError

# ── Test model ──────────────────────────────────────────────────────────

class FakeModel(BaseModel):
    name: str = "test"
    value: int = 42


# ── OutputContext ───────────────────────────────────────────────────────


class TestOutputContext:
    def test_default_context_values(self):
        from reddit_cli.output import OutputContext
        ctx = OutputContext.from_flags()
        assert ctx.compact is False
        assert ctx.full_text is False

    def test_from_flags_json(self):
        from reddit_cli.output import OutputContext
        ctx = OutputContext.from_flags(as_json=True)
        assert ctx.format == "json"

    def test_from_flags_yaml(self):
        from reddit_cli.output import OutputContext
        ctx = OutputContext.from_flags(as_yaml=True)
        assert ctx.format == "yaml"

    def test_from_flags_compact(self):
        from reddit_cli.output import OutputContext
        ctx = OutputContext.from_flags(compact=True)
        assert ctx.compact is True


# ── emit() ─────────────────────────────────────────────────────────────


class TestEmit:
    def test_emit_json_when_explicit_flag(self, capsys):
        from reddit_cli.output import OutputContext, emit
        ctx = OutputContext.from_flags(as_json=True)
        emit(FakeModel(), ctx)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert data["data"]["name"] == "test"

    def test_emit_yaml_when_explicit_flag(self, capsys):
        from reddit_cli.output import OutputContext, emit
        ctx = OutputContext.from_flags(as_yaml=True)
        emit(FakeModel(), ctx)
        captured = capsys.readouterr()
        assert "ok: true" in captured.out
        assert "name: test" in captured.out

    def test_emit_json_when_not_tty(self, capsys):
        from reddit_cli.output import OutputContext, emit
        ctx = OutputContext.from_flags()  # no explicit flag
        # CliRunner/capsys is not a TTY, so should default to JSON
        emit(FakeModel(), ctx)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True

    def test_emit_calls_render_when_tty(self):
        from reddit_cli.output import OutputContext, emit
        ctx = OutputContext.from_flags()
        rendered = []

        with patch("reddit_cli.output.sys") as mock_sys:
            mock_sys.stdout = StringIO()
            mock_sys.stdout.isatty = lambda: True
            emit(FakeModel(), ctx, render=lambda d: rendered.append(d))

        assert len(rendered) == 1
        assert rendered[0].name == "test"

    def test_emit_compact_strips_fields(self, capsys):
        from reddit_cli.models import Listing, Post
        from reddit_cli.output import OutputContext, emit

        post = Post(
            id="1", title="Test", author="u", subreddit="s", score=1,
            upvote_ratio=1.0, num_comments=0, created_utc=0, permalink="/",
            url="/", selftext="body", domain="self", is_self=True,
            over_18=False, spoiler=False, stickied=False, locked=False,
            is_video=False,
        )
        listing = Listing(posts=[post], after=None, count=1)
        ctx = OutputContext.from_flags(as_json=True, compact=True)
        emit(listing, ctx)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        # Compact should strip non-essential fields like selftext
        post_data = data["data"]["posts"][0]
        assert "id" in post_data
        assert "selftext" not in post_data


# ── exit_for_error() ───────────────────────────────────────────────────


class TestExitForError:
    def test_json_mode_outputs_envelope(self, capsys):
        from reddit_cli.output import OutputContext, exit_for_error
        ctx = OutputContext.from_flags(as_json=True)
        exc = RedditAPIError(message="Something broke")
        with pytest.raises(SystemExit):
            exit_for_error(exc, ctx)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is False
        assert "Something broke" in data["error"]["message"]

    def test_uses_error_code_for_exception(self, capsys):
        from reddit_cli.output import OutputContext, exit_for_error
        ctx = OutputContext.from_flags(as_json=True)
        exc = NotFoundError()
        with pytest.raises(SystemExit):
            exit_for_error(exc, ctx)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"]["code"] == "not_found"

    def test_raises_system_exit(self):
        from reddit_cli.output import OutputContext, exit_for_error
        ctx = OutputContext.from_flags(as_json=True)
        with pytest.raises(SystemExit) as exc_info:
            exit_for_error(RedditAPIError(message="fail"), ctx)
        assert exc_info.value.code == 1

    def test_tty_mode_shows_rich_error(self):
        from reddit_cli.output import OutputContext, exit_for_error
        ctx = OutputContext.from_flags()
        stderr_buf = StringIO()

        with patch("reddit_cli.output.sys") as mock_sys:
            mock_sys.stdout = StringIO()
            mock_sys.stdout.isatty = lambda: True
            mock_sys.stderr = stderr_buf
            with pytest.raises(SystemExit):
                exit_for_error(RedditAPIError(message="oops"), ctx)
