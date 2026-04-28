"""Tests for handle_command() orchestrator."""

import json
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from reddit_cli.errors import NotFoundError
from reddit_cli.models import Listing, Post


def _make_post(**kw):
    defaults = dict(
        id="1", title="T", author="a", subreddit="s", score=1,
        upvote_ratio=1.0, num_comments=0, created_utc=0.0, permalink="/",
        url="/", selftext="", domain="self", is_self=True,
        over_18=False, spoiler=False, stickied=False, locked=False,
        is_video=False,
    )
    defaults.update(kw)
    return Post(**defaults)


class TestHandleCommand:
    def test_action_result_emitted_as_json(self, capsys):
        from reddit_cli.commands.helpers import handle_command
        from reddit_cli.output import OutputContext

        class Result(BaseModel):
            msg: str = "ok"

        ctx = OutputContext.from_flags(as_json=True)
        handle_command(action=lambda: Result(), ctx=ctx)
        data = json.loads(capsys.readouterr().out)
        assert data["ok"] is True
        assert data["data"]["msg"] == "ok"

    def test_action_result_rendered_when_tty(self):
        from reddit_cli.commands.helpers import handle_command
        from reddit_cli.output import OutputContext

        class Result(BaseModel):
            msg: str = "ok"

        rendered = []
        ctx = OutputContext.from_flags()

        with patch("reddit_cli.output.sys") as mock_sys:
            from io import StringIO
            mock_sys.stdout = StringIO()
            mock_sys.stdout.isatty = lambda: True
            handle_command(action=lambda: Result(), ctx=ctx, render=lambda d: rendered.append(d))

        assert len(rendered) == 1

    def test_api_error_emits_error_and_exits(self, capsys):
        from reddit_cli.commands.helpers import handle_command
        from reddit_cli.output import OutputContext

        ctx = OutputContext.from_flags(as_json=True)
        with pytest.raises(SystemExit):
            handle_command(
                action=lambda: (_ for _ in ()).throw(NotFoundError()),
                ctx=ctx,
            )
        data = json.loads(capsys.readouterr().out)
        assert data["ok"] is False

    def test_api_error_exit_code_propagated(self):
        from reddit_cli.commands.helpers import handle_command
        from reddit_cli.output import OutputContext

        ctx = OutputContext.from_flags(as_json=True)
        with pytest.raises(SystemExit) as exc_info:
            handle_command(
                action=lambda: (_ for _ in ()).throw(NotFoundError()),
                ctx=ctx,
            )
        assert exc_info.value.code == 3  # NOT_FOUND exit code

    @patch("reddit_cli.commands.helpers.save_index")
    def test_listing_saves_index(self, mock_save):
        from reddit_cli.commands.helpers import handle_command
        from reddit_cli.output import OutputContext

        listing = Listing(posts=[_make_post()], after=None, count=1)
        ctx = OutputContext.from_flags(as_json=True)
        handle_command(action=lambda: listing, ctx=ctx, save_listing=True)
        mock_save.assert_called_once()

    @patch("reddit_cli.commands.helpers.save_index")
    def test_non_listing_skips_save_index(self, mock_save):
        from reddit_cli.commands.helpers import handle_command
        from reddit_cli.output import OutputContext

        class Result(BaseModel):
            msg: str = "ok"

        ctx = OutputContext.from_flags(as_json=True)
        handle_command(action=lambda: Result(), ctx=ctx, save_listing=True)
        mock_save.assert_not_called()
