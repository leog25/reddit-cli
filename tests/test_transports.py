"""Tests for ReadTransport and WriteTransport."""

import json
from unittest.mock import patch

import httpx
import pytest


def make_json_response(data: dict, status_code: int = 200, headers: dict | None = None):
    content = json.dumps(data).encode("utf-8")
    resp_headers = {"content-type": "application/json"}
    if headers:
        resp_headers.update(headers)
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=resp_headers,
        request=httpx.Request("GET", "https://www.reddit.com/test"),
    )


def make_session(cookies: dict | None = None, modhash: str | None = None):
    from reddit_cli.session import SessionState

    session = SessionState(
        cookies=cookies or {},
        modhash=modhash,
    )
    session.refresh_capabilities()
    return session


def make_read_transport(handler, session=None, delay=0.0):
    from reddit_cli.config import RuntimeConfig
    from reddit_cli.fingerprint import BrowserFingerprint
    from reddit_cli.transports import ReadTransport

    config = RuntimeConfig(read_request_delay=delay, max_retries=3)
    transport = ReadTransport(
        session=session or make_session(),
        config=config,
        fingerprint=BrowserFingerprint.chrome133_mac(),
        request_delay=delay,
        _transport=httpx.MockTransport(handler),
    )
    return transport


def make_write_transport(handler, session=None, delay=0.0):
    from reddit_cli.config import RuntimeConfig
    from reddit_cli.fingerprint import BrowserFingerprint
    from reddit_cli.transports import WriteTransport

    config = RuntimeConfig(write_request_delay=delay, max_retries=3)
    transport = WriteTransport(
        session=session or make_session(cookies={"reddit_session": "x"}, modhash="mh123"),
        config=config,
        fingerprint=BrowserFingerprint.chrome133_mac(),
        request_delay=delay,
        _transport=httpx.MockTransport(handler),
    )
    return transport


class TestReadTransport:
    @patch("time.sleep")
    def test_returns_json(self, mock_sleep):
        transport = make_read_transport(
            lambda req: make_json_response({"kind": "Listing", "data": {}})
        )
        result = transport.request("GET", "/r/python.json")
        assert result["kind"] == "Listing"

    @patch("time.sleep")
    def test_404_raises_not_found(self, mock_sleep):
        from reddit_cli.errors import NotFoundError

        transport = make_read_transport(
            lambda req: make_json_response({}, status_code=404)
        )
        with pytest.raises(NotFoundError):
            transport.request("GET", "/r/nonexistent.json")

    @patch("time.sleep")
    def test_403_raises_forbidden(self, mock_sleep):
        from reddit_cli.errors import ForbiddenError

        transport = make_read_transport(
            lambda req: make_json_response({}, status_code=403)
        )
        with pytest.raises(ForbiddenError):
            transport.request("GET", "/r/private.json")

    @patch("time.sleep")
    def test_401_raises_session_expired(self, mock_sleep):
        from reddit_cli.errors import SessionExpiredError

        transport = make_read_transport(
            lambda req: make_json_response({}, status_code=401)
        )
        with pytest.raises(SessionExpiredError):
            transport.request("GET", "/api/v1/me")

    @patch("time.sleep")
    def test_429_retries_then_raises(self, mock_sleep):
        from reddit_cli.errors import RateLimitError

        call_count = 0

        def always_429(req):
            nonlocal call_count
            call_count += 1
            return make_json_response({}, status_code=429, headers={"Retry-After": "1"})

        transport = make_read_transport(always_429)
        with pytest.raises(RateLimitError):
            transport.request("GET", "/test")
        assert call_count == 3  # max_retries

    @patch("time.sleep")
    def test_429_retry_succeeds(self, mock_sleep):
        call_count = 0

        def retry_then_ok(req):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return make_json_response({}, status_code=429, headers={"Retry-After": "1"})
            return make_json_response({"ok": True})

        transport = make_read_transport(retry_then_ok)
        result = transport.request("GET", "/test")
        assert result["ok"] is True
        assert call_count == 2

    @patch("time.sleep")
    def test_5xx_retries_with_backoff(self, mock_sleep):
        call_count = 0

        def fail_then_ok(req):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return make_json_response({}, status_code=500)
            return make_json_response({"ok": True})

        transport = make_read_transport(fail_then_ok)
        result = transport.request("GET", "/test")
        assert result["ok"] is True
        assert call_count == 3

    @patch("time.sleep")
    def test_html_response_raises_error(self, mock_sleep):
        from reddit_cli.errors import RedditAPIError

        transport = make_read_transport(
            lambda req: httpx.Response(
                200,
                content=b"<html><body>Login</body></html>",
                headers={"content-type": "text/html"},
                request=httpx.Request("GET", "https://www.reddit.com/test"),
            )
        )
        with pytest.raises(RedditAPIError, match="HTML"):
            transport.request("GET", "/test")

    @patch("time.sleep")
    def test_request_count_increments(self, mock_sleep):
        transport = make_read_transport(
            lambda req: make_json_response({"ok": True})
        )
        assert transport.request_count == 0
        transport.request("GET", "/test1")
        assert transport.request_count == 1
        transport.request("GET", "/test2")
        assert transport.request_count == 2

    def test_uses_chrome_fingerprint_headers(self):
        captured = []

        def capture(req):
            captured.append(req)
            return make_json_response({})

        transport = make_read_transport(capture)
        with patch("time.sleep"):
            transport.request("GET", "/test")

        ua = captured[0].headers.get("user-agent", "")
        assert "Chrome/133" in ua


class TestWriteTransport:
    @patch("reddit_cli.transports.time.sleep")
    def test_write_succeeds_with_auth(self, mock_sleep):
        transport = make_write_transport(
            lambda req: make_json_response({"success": True})
        )
        result = transport.request("POST", "/api/vote", data={"id": "t3_abc", "dir": "1"})
        assert result["success"] is True

    @patch("reddit_cli.transports.time.sleep")
    def test_write_fails_without_capability(self, mock_sleep):
        from reddit_cli.errors import RedditAPIError

        session = make_session(cookies={})  # no reddit_session -> no capabilities
        transport = make_write_transport(
            lambda req: make_json_response({}),
            session=session,
        )
        with pytest.raises(RedditAPIError, match="not write-capable"):
            transport.request("POST", "/api/vote", data={})

    @patch("reddit_cli.transports.time.sleep")
    def test_write_injects_modhash(self, mock_sleep):
        captured = []

        def capture(req):
            captured.append(req)
            return make_json_response({"success": True})

        session = make_session(cookies={"reddit_session": "x"}, modhash="mh_test")
        transport = make_write_transport(capture, session=session)
        transport.request("POST", "/api/vote", data={"id": "t3_abc", "dir": "1"})

        body = captured[0].content.decode("utf-8")
        assert "uh=mh_test" in body

    @patch("reddit_cli.transports.time.sleep")
    def test_write_headers_include_origin(self, mock_sleep):
        captured = []

        def capture(req):
            captured.append(req)
            return make_json_response({})

        transport = make_write_transport(capture)
        transport.request("POST", "/api/vote", data={"id": "t3_abc"})

        headers = dict(captured[0].headers)
        assert "origin" in headers or "Origin" in headers


class TestJitter:
    def test_jitter_called_when_delay_set(self):
        import time as _time

        sleep_calls = []
        transport = make_read_transport(
            lambda req: make_json_response({"ok": True}),
            delay=1.0,
        )
        transport._last_request_time = _time.time()

        with patch("reddit_cli.transports.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            transport.request("GET", "/test")

        assert len(sleep_calls) > 0
        assert sleep_calls[0] > 0
