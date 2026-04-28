"""Tests for RedditClient transport integration (v3 refactor)."""

import json
import pathlib
from unittest.mock import patch

import httpx
import pytest

from reddit_cli.auth import Credential
from reddit_cli.client import RedditClient
from reddit_cli.errors import NotFoundError, RateLimitError
from reddit_cli.session import SessionState

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


# ── Helpers ────────────────────────────────────────────────────────────

def _json_response(
    data: dict, status_code: int = 200, headers: dict | None = None,
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(data).encode(),
        headers=headers or {"content-type": "application/json"},
        request=httpx.Request("GET", "https://www.reddit.com/test"),
    )


def _noop_handler(request: httpx.Request) -> httpx.Response:
    """Default handler that returns empty JSON for any request."""
    return _json_response({"data": {"children": [], "after": None}})


# ── C1: Context Manager ───────────────────────────────────────────────


class TestContextManager:
    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_enter_returns_self(self, _mock_cred):
        client = RedditClient(_transport=httpx.MockTransport(_noop_handler))
        with client as ctx:
            assert ctx is client

    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_exit_closes_client(self, _mock_cred):
        client = RedditClient(_transport=httpx.MockTransport(_noop_handler))
        with client:
            pass
        assert client._client.is_closed

    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_exit_closes_on_exception(self, _mock_cred):
        client = RedditClient(_transport=httpx.MockTransport(_noop_handler))
        with pytest.raises(RuntimeError):
            with client:
                raise RuntimeError("boom")
        assert client._client.is_closed


# ── C2: SessionState in Constructor ───────────────────────────────────


ME_RESPONSE = {"data": {"name": "testuser", "modhash": "fetched_mh"}}


class TestSessionInit:
    @patch("reddit_cli.auth.load_credential")
    def test_session_created_from_credentials(self, mock_load):
        mock_load.return_value = Credential(
            cookies={"reddit_session": "abc"},
            modhash="saved_mh",
        )

        def handler(req: httpx.Request) -> httpx.Response:
            return _json_response(ME_RESPONSE)

        client = RedditClient(_transport=httpx.MockTransport(handler))
        assert isinstance(client._session, SessionState)
        assert client._session.cookies.get("reddit_session") == "abc"

    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_session_without_credentials(self, _mock):
        client = RedditClient(_transport=httpx.MockTransport(_noop_handler))
        assert isinstance(client._session, SessionState)
        assert client._session.cookies == {}
        assert client._session.can_write is False

    @patch("reddit_cli.auth.load_credential")
    def test_modhash_from_credential_used(self, mock_load):
        mock_load.return_value = Credential(
            cookies={"reddit_session": "abc"},
            modhash="saved_mh",
        )
        client = RedditClient(_transport=httpx.MockTransport(_noop_handler))
        assert client._session.modhash == "saved_mh"
        assert client._session.can_write is True

    @patch("reddit_cli.auth.load_credential")
    def test_no_modhash_means_no_write(self, mock_load):
        mock_load.return_value = Credential(cookies={"reddit_session": "abc"})
        client = RedditClient(_transport=httpx.MockTransport(_noop_handler))
        assert client._session.is_authenticated is True
        assert client._session.can_write is False


# ── C3: ReadTransport Integration ─────────────────────────────────────


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _make_client(handler, cred=None):
    """Create a RedditClient with mocked credential and transport."""
    with patch("reddit_cli.auth.load_credential", return_value=cred):
        return RedditClient(_transport=httpx.MockTransport(handler))


class TestReadTransportIntegration:
    def test_get_listing_uses_fingerprint_headers(self):
        captured = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(req)
            return _json_response(_load_fixture("subreddit_listing.json"))

        client = _make_client(handler)
        client.get_listing("python", "hot")
        assert len(captured) >= 1
        req = captured[-1]
        ua = req.headers.get("user-agent", "")
        assert "Chrome" in ua or "reddit-cli" in ua

    @patch("reddit_cli.transports.time.sleep")
    def test_retries_on_5xx(self, mock_sleep):
        calls = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(1)
            if len(calls) < 3:
                return _json_response({"error": "server"}, status_code=500)
            return _json_response(_load_fixture("subreddit_listing.json"))

        client = _make_client(handler)
        listing = client.get_listing("python", "hot")
        assert len(listing.posts) == 3
        assert len(calls) == 3

    def test_404_raises_not_found(self):
        def handler(req: httpx.Request) -> httpx.Response:
            return _json_response({"error": "not found"}, status_code=404)

        client = _make_client(handler)
        with pytest.raises(NotFoundError):
            client.get_listing("nonexistent", "hot")

    @patch("reddit_cli.transports.time.sleep")
    def test_429_raises_rate_limit_error(self, mock_sleep):
        def handler(req: httpx.Request) -> httpx.Response:
            return _json_response({}, status_code=429, headers={
                "content-type": "application/json",
                "Retry-After": "1",
            })

        client = _make_client(handler)
        with pytest.raises(RateLimitError):
            client.get_listing("python", "hot")

    def test_search_uses_transport(self):
        def handler(req: httpx.Request) -> httpx.Response:
            return _json_response(_load_fixture("search_results.json"))

        client = _make_client(handler)
        listing = client.search("test query")
        assert len(listing.posts) >= 1


# ── C4: WriteTransport Integration ────────────────────────────────────


def _make_write_client(handler):
    """Create an authenticated client with modhash for write operations."""
    cred = Credential(cookies={"reddit_session": "abc"}, modhash="test_mh")
    return _make_client(handler, cred=cred)


class TestWriteTransportIntegration:
    def test_vote_uses_write_transport(self):
        captured = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(req)
            return _json_response({"success": True})

        client = _make_write_client(handler)
        client.vote("t3_abc", direction=1)
        req = captured[-1]
        assert req.method == "POST"
        assert "x-modhash" in req.headers
        assert b"id=t3_abc" in req.content

    def test_vote_without_auth_raises(self):
        client = _make_client(lambda r: _json_response({}))
        from reddit_cli.errors import RedditAPIError
        with pytest.raises(RedditAPIError):
            client.vote("t3_abc", direction=1)

    def test_save_uses_write_transport(self):
        captured = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(req)
            return _json_response({"success": True})

        client = _make_write_client(handler)
        client.save_item("t3_abc")
        req = captured[-1]
        assert b"id=t3_abc" in req.content

    def test_post_comment_uses_write_transport(self):
        captured = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(req)
            return _json_response({"success": True})

        client = _make_write_client(handler)
        client.post_comment("t3_abc", "Hello!")
        req = captured[-1]
        assert b"parent=t3_abc" in req.content
        assert b"text=Hello" in req.content

    @patch("reddit_cli.transports.time.sleep")
    def test_write_retries_on_5xx(self, mock_sleep):
        calls = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(1)
            if len(calls) < 3:
                return _json_response({}, status_code=500)
            return _json_response({"success": True})

        client = _make_write_client(handler)
        client.vote("t3_abc", direction=1)
        assert len(calls) == 3

    def test_old_ensure_modhash_removed(self):
        client = _make_client(lambda r: _json_response({}))
        assert not hasattr(client, '_modhash') or client._modhash is None


# ── C5: get_more_children via Transport ───────────────────────────────


class TestMoreChildrenTransport:
    @patch("reddit_cli.transports.time.sleep")
    def test_uses_transport_not_fresh_client(self, mock_sleep):
        """Verify morechildren goes through the read transport, not a fresh httpx.Client."""
        captured = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(req)
            return _json_response(_load_fixture("morechildren.json"))

        client = _make_client(handler)
        client.get_more_children("t3_abc", ["id1", "id2"])
        assert any("/api/morechildren" in str(r.url) for r in captured)

    @patch("reddit_cli.transports.time.sleep")
    def test_batching_still_works(self, mock_sleep):
        calls = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(str(req.url))
            return _json_response(_load_fixture("morechildren.json"))

        client = _make_client(handler)
        ids = [f"id{i}" for i in range(150)]
        client.get_more_children("t3_abc", ids)
        morechildren_calls = [u for u in calls if "morechildren" in u]
        assert len(morechildren_calls) == 2  # 100 + 50


# ── C7: Cleanup Verification ─────────────────────────────────────────


class TestCleanup:
    def test_no_throttle_method(self):
        assert not hasattr(RedditClient, '_throttle')

    def test_no_do_request_method(self):
        assert not hasattr(RedditClient, '_do_request')

    def test_no_check_response_method(self):
        assert not hasattr(RedditClient, '_check_response')

    def test_context_manager_closes_transports(self):
        client = _make_client(lambda r: _json_response({}))
        with client:
            pass
        assert client._read_transport._http.is_closed
        assert client._write_transport._http.is_closed

    def test_startup_still_lazy(self):
        """Verify httpx is not imported when just loading the CLI app."""
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; from reddit_cli.main import cli; assert 'httpx' not in sys.modules"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
