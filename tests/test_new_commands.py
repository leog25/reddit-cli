"""Tests for new commands: whoami, saved, upvoted."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

runner = CliRunner()

ME_DATA = {
    "data": {
        "name": "testuser",
        "id": "abc",
        "link_karma": 100,
        "comment_karma": 200,
        "total_karma": 300,
        "created_utc": 1609459200.0,
        "is_gold": False,
        "is_mod": False,
        "is_employee": False,
        "has_verified_email": True,
        "icon_img": "",
    }
}


class TestWhoami:
    @patch("reddit_cli.client.RedditClient")
    @patch("reddit_cli.auth.load_credential")
    def test_returns_user_info_json(self, mock_load, MockClient):
        from reddit_cli.auth import Credential
        from reddit_cli.main import app

        mock_load.return_value = Credential(cookies={"reddit_session": "abc"}, modhash="mh")
        instance = MockClient.return_value
        from reddit_cli.models import UserInfo
        instance.get_me.return_value = UserInfo(**ME_DATA["data"])

        result = runner.invoke(app, ["auth", "whoami"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["name"] == "testuser"

    @patch("reddit_cli.client.RedditClient")
    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_requires_auth(self, mock_load, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["auth", "whoami"])
        assert result.exit_code == 1


class TestSaved:
    @patch("reddit_cli.client.RedditClient")
    @patch("reddit_cli.auth.load_credential")
    def test_returns_listing(self, mock_load, MockClient):
        from reddit_cli.auth import Credential
        from reddit_cli.main import app
        from reddit_cli.models import Listing

        mock_load.return_value = Credential(
            cookies={"reddit_session": "abc"}, modhash="mh", username="testuser",
        )
        instance = MockClient.return_value
        instance.get_saved.return_value = Listing(posts=[], after=None, count=0)

        result = runner.invoke(app, ["saved"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    @patch("reddit_cli.client.RedditClient")
    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_requires_auth(self, mock_load, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["saved"])
        assert result.exit_code == 1


class TestUpvoted:
    @patch("reddit_cli.client.RedditClient")
    @patch("reddit_cli.auth.load_credential")
    def test_returns_listing(self, mock_load, MockClient):
        from reddit_cli.auth import Credential
        from reddit_cli.main import app
        from reddit_cli.models import Listing

        mock_load.return_value = Credential(
            cookies={"reddit_session": "abc"}, modhash="mh", username="testuser",
        )
        instance = MockClient.return_value
        instance.get_upvoted.return_value = Listing(posts=[], after=None, count=0)

        result = runner.invoke(app, ["upvoted"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    @patch("reddit_cli.client.RedditClient")
    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_requires_auth(self, mock_load, MockClient):
        from reddit_cli.main import app

        result = runner.invoke(app, ["upvoted"])
        assert result.exit_code == 1
