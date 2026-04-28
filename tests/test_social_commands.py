"""Tests for write commands: vote, save, subscribe, comment."""

from unittest.mock import patch

from typer.testing import CliRunner

runner = CliRunner()


class TestVoteCommand:
    @patch("reddit_cli.client.RedditClient")
    def test_vote_upvote(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.vote.return_value = {"success": True}

        result = runner.invoke(app, ["vote", "t3_abc123"])
        assert result.exit_code == 0
        instance.vote.assert_called_once_with("t3_abc123", direction=1)

    @patch("reddit_cli.client.RedditClient")
    def test_vote_downvote(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.vote.return_value = {"success": True}

        result = runner.invoke(app, ["vote", "t3_abc123", "--down"])
        assert result.exit_code == 0
        instance.vote.assert_called_once_with("t3_abc123", direction=-1)

    @patch("reddit_cli.client.RedditClient")
    def test_vote_undo(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.vote.return_value = {"success": True}

        result = runner.invoke(app, ["vote", "t3_abc123", "--undo"])
        assert result.exit_code == 0
        instance.vote.assert_called_once_with("t3_abc123", direction=0)


class TestSaveCommand:
    @patch("reddit_cli.client.RedditClient")
    def test_save(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.save_item.return_value = {}

        result = runner.invoke(app, ["save", "t3_abc123"])
        assert result.exit_code == 0
        instance.save_item.assert_called_once_with("t3_abc123")

    @patch("reddit_cli.client.RedditClient")
    def test_unsave(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.unsave_item.return_value = {}

        result = runner.invoke(app, ["save", "t3_abc123", "--undo"])
        assert result.exit_code == 0
        instance.unsave_item.assert_called_once_with("t3_abc123")


class TestSubscribeCommand:
    @patch("reddit_cli.client.RedditClient")
    def test_subscribe(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.subscribe.return_value = {}

        result = runner.invoke(app, ["subscribe", "python"])
        assert result.exit_code == 0
        instance.subscribe.assert_called_once_with("python", action="sub")

    @patch("reddit_cli.client.RedditClient")
    def test_unsubscribe(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.subscribe.return_value = {}

        result = runner.invoke(app, ["subscribe", "python", "--undo"])
        assert result.exit_code == 0
        instance.subscribe.assert_called_once_with("python", action="unsub")


class TestCommentCommand:
    @patch("reddit_cli.client.RedditClient")
    def test_comment(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.post_comment.return_value = {"json": {"data": {"things": []}}}

        result = runner.invoke(app, ["comment", "t3_abc123", "Great post!"])
        assert result.exit_code == 0
        instance.post_comment.assert_called_once_with("t3_abc123", "Great post!")
