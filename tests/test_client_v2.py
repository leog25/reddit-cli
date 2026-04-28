"""Tests for new client methods: write ops, new reads, fullname resolver."""

import json
from pathlib import Path
from unittest.mock import patch

import httpx

from reddit_cli.client import RedditClient

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


def make_json_response(data: dict, status_code: int = 200):
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(data).encode("utf-8"),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://www.reddit.com/test"),
    )


def make_listing_response():
    return make_json_response(load_fixture("subreddit_listing.json"))


def _write_handler(captured: list):
    """Handler that captures write requests."""
    def handler(req):
        captured.append(req)
        return make_json_response({"success": True})
    return handler


def _make_write_client(handler):
    """Create an authenticated client with modhash for write operations."""
    from reddit_cli.auth import Credential
    cred = Credential(cookies={"reddit_session": "abc"}, modhash="fake_modhash")
    with patch("reddit_cli.auth.load_credential", return_value=cred):
        return RedditClient(_transport=httpx.MockTransport(handler))


class TestWriteMethods:
    @patch("reddit_cli.transports.time.sleep")
    def test_vote_sends_correct_data(self, mock_sleep):
        captured = []
        client = _make_write_client(_write_handler(captured))
        client.vote("t3_abc123", direction=1)

        body = captured[0].content.decode("utf-8")
        assert "id=t3_abc123" in body
        assert "dir=1" in body

    @patch("reddit_cli.transports.time.sleep")
    def test_vote_downvote(self, mock_sleep):
        captured = []
        client = _make_write_client(_write_handler(captured))
        client.vote("t3_abc", direction=-1)

        body = captured[0].content.decode("utf-8")
        assert "dir=-1" in body

    @patch("reddit_cli.transports.time.sleep")
    def test_save_item(self, mock_sleep):
        captured = []
        client = _make_write_client(_write_handler(captured))
        client.save_item("t3_abc123")

        assert "/api/save" in str(captured[0].url)
        assert "id=t3_abc123" in captured[0].content.decode("utf-8")

    @patch("reddit_cli.transports.time.sleep")
    def test_unsave_item(self, mock_sleep):
        captured = []
        client = _make_write_client(_write_handler(captured))
        client.unsave_item("t3_abc123")

        assert "/api/unsave" in str(captured[0].url)

    @patch("reddit_cli.transports.time.sleep")
    def test_subscribe(self, mock_sleep):
        captured = []
        client = _make_write_client(_write_handler(captured))
        client.subscribe("python", action="sub")

        body = captured[0].content.decode("utf-8")
        assert "sr_name=python" in body
        assert "action=sub" in body

    @patch("reddit_cli.transports.time.sleep")
    def test_post_comment(self, mock_sleep):
        captured = []
        client = _make_write_client(_write_handler(captured))
        client.post_comment("t3_abc123", "Great post!")

        body = captured[0].content.decode("utf-8")
        assert "parent=t3_abc123" in body
        assert "text=Great" in body


class TestNewReadMethods:
    @patch("time.sleep")
    def test_get_popular(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(req):
            captured.append(req)
            return make_listing_response()

        client = RedditClient(_transport=httpx.MockTransport(capture))
        listing = client.get_popular(limit=5)

        assert "/r/popular" in str(captured[0].url)
        assert len(listing.posts) > 0

    @patch("time.sleep")
    def test_get_all(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(req):
            captured.append(req)
            return make_listing_response()

        client = RedditClient(_transport=httpx.MockTransport(capture))
        client.get_all(limit=5)

        assert "/r/all" in str(captured[0].url)

    @patch("time.sleep")
    def test_get_home(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(req):
            captured.append(req)
            return make_listing_response()

        client = RedditClient(_transport=httpx.MockTransport(capture))
        client.get_home(limit=5)

        url = str(captured[0].url)
        assert url.endswith(".json") or "/.json" in url

    @patch("time.sleep")
    def test_get_user_posts(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(req):
            captured.append(req)
            return make_listing_response()

        client = RedditClient(_transport=httpx.MockTransport(capture))
        client.get_user_posts("spez", limit=3)

        assert "/user/spez/submitted" in str(captured[0].url)

    @patch("time.sleep")
    def test_get_user_comments(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(req):
            captured.append(req)
            return make_listing_response()

        client = RedditClient(_transport=httpx.MockTransport(capture))
        # Returns raw listing data (comments don't fit Post model, return raw)
        client.get_user_comments("spez", limit=3)

        assert "/user/spez/comments" in str(captured[0].url)


class TestFullnameResolver:
    def test_bare_id(self):
        from reddit_cli.client import resolve_fullname

        assert resolve_fullname("abc123") == "t3_abc123"

    def test_already_fullname(self):
        from reddit_cli.client import resolve_fullname

        assert resolve_fullname("t3_abc123") == "t3_abc123"
        assert resolve_fullname("t1_xyz") == "t1_xyz"

    def test_numeric_index_passthrough(self):
        from reddit_cli.client import resolve_fullname

        # Pure digits are index lookups, not fullnames — return as-is for caller to resolve
        assert resolve_fullname("3") == "3"
