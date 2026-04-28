import json
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


def make_response(fixture_name: str, status_code: int = 200, headers: dict = None):
    """Create a mock httpx.Response from a fixture file."""
    data = load_fixture(fixture_name)
    content = json.dumps(data).encode("utf-8")
    resp_headers = {"content-type": "application/json; charset=UTF-8"}
    if headers:
        resp_headers.update(headers)
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=resp_headers,
        request=httpx.Request("GET", "https://www.reddit.com/test"),
    )


def make_error_response(status_code: int, body: str = ""):
    return httpx.Response(
        status_code=status_code,
        content=body.encode("utf-8"),
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", "https://www.reddit.com/test"),
    )


# --- Listing parsing tests ---


class TestGetListing:
    @patch("time.sleep")
    def test_returns_listing_with_posts(self, mock_sleep):
        from reddit_cli.client import RedditClient

        transport = httpx.MockTransport(
            lambda req: make_response("subreddit_listing.json")
        )
        client = RedditClient(_transport=transport)
        listing = client.get_listing("python", "hot", limit=3)

        assert len(listing.posts) > 0
        assert listing.count == len(listing.posts)
        for post in listing.posts:
            assert post.id
            assert post.title
            assert post.subreddit

    @patch("time.sleep")
    def test_listing_has_after_cursor(self, mock_sleep):
        from reddit_cli.client import RedditClient

        transport = httpx.MockTransport(
            lambda req: make_response("subreddit_listing.json")
        )
        client = RedditClient(_transport=transport)
        listing = client.get_listing("python", "hot", limit=3)

        # after is either None or a string pagination cursor
        assert listing.after is None or isinstance(listing.after, str)

    @patch("time.sleep")
    def test_listing_url_params(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured_requests = []

        def capture_transport(request):
            captured_requests.append(request)
            return make_response("subreddit_listing.json")

        transport = httpx.MockTransport(capture_transport)
        client = RedditClient(_transport=transport)
        client.get_listing("python", "top", limit=50, time="week", after="abc123")

        req = captured_requests[0]
        assert "/r/python/top.json" in str(req.url)
        assert "limit=50" in str(req.url)
        assert "t=week" in str(req.url)
        assert "after=abc123" in str(req.url)


# --- Subreddit info tests ---


class TestGetSubredditInfo:
    @patch("time.sleep")
    def test_returns_subreddit_info(self, mock_sleep):
        from reddit_cli.client import RedditClient

        transport = httpx.MockTransport(
            lambda req: make_response("subreddit_about.json")
        )
        client = RedditClient(_transport=transport)
        info = client.get_subreddit_info("python")

        assert info.display_name == "Python"
        assert isinstance(info.subscribers, int)
        assert info.subscribers > 0

    @patch("time.sleep")
    def test_subreddit_info_url(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("subreddit_about.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_subreddit_info("python")

        assert "/r/python/about.json" in str(captured[0].url)


# --- Post + comments tests ---


class TestGetPost:
    @patch("time.sleep")
    def test_returns_post_detail(self, mock_sleep):
        from reddit_cli.client import RedditClient

        transport = httpx.MockTransport(
            lambda req: make_response("post_comments.json")
        )
        client = RedditClient(_transport=transport)
        detail = client.get_post("1s0gfyb")

        assert detail.post.id == "1s0gfyb"
        assert detail.post.title

    @patch("time.sleep")
    def test_comments_parsed(self, mock_sleep):
        from reddit_cli.client import RedditClient
        from reddit_cli.models import Comment

        transport = httpx.MockTransport(
            lambda req: make_response("post_comments.json")
        )
        client = RedditClient(_transport=transport)
        detail = client.get_post("1s0gfyb")

        # Should have at least one parsed comment
        comments = [c for c in detail.comments if isinstance(c, Comment)]
        assert len(comments) > 0
        assert comments[0].author
        assert comments[0].body

    @patch("time.sleep")
    def test_nested_replies_parsed(self, mock_sleep):
        from reddit_cli.client import RedditClient
        from reddit_cli.models import Comment

        transport = httpx.MockTransport(
            lambda req: make_response("post_comments.json")
        )
        client = RedditClient(_transport=transport)
        detail = client.get_post("1s0gfyb")

        # Find a comment with replies (second comment in fixture has nested replies)
        comments_with_replies = [
            c
            for c in detail.comments
            if isinstance(c, Comment) and len(c.replies) > 0
        ]
        # The fixture has at least one comment with replies
        assert len(comments_with_replies) > 0
        reply = comments_with_replies[0].replies[0]
        assert isinstance(reply, Comment)
        assert reply.author


# --- User info tests ---


class TestGetUserInfo:
    @patch("time.sleep")
    def test_returns_user_info(self, mock_sleep):
        from reddit_cli.client import RedditClient

        transport = httpx.MockTransport(
            lambda req: make_response("user_about.json")
        )
        client = RedditClient(_transport=transport)
        user = client.get_user_info("spez")

        assert user.name == "spez"
        assert user.total_karma > 0

    @patch("time.sleep")
    def test_user_info_url(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("user_about.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_user_info("spez")

        assert "/user/spez/about.json" in str(captured[0].url)


# --- Search tests ---


class TestSearch:
    @patch("time.sleep")
    def test_returns_search_results(self, mock_sleep):
        from reddit_cli.client import RedditClient

        transport = httpx.MockTransport(
            lambda req: make_response("search_results.json")
        )
        client = RedditClient(_transport=transport)
        listing = client.search("asyncio", subreddit="python")

        assert len(listing.posts) > 0

    @patch("time.sleep")
    def test_search_url_with_subreddit(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("search_results.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.search("asyncio", subreddit="python")

        url = str(captured[0].url)
        assert "/r/python/search.json" in url
        assert "q=asyncio" in url
        assert "restrict_sr=1" in url

    @patch("time.sleep")
    def test_search_url_global(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("search_results.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.search("asyncio")

        url = str(captured[0].url)
        assert "/search.json" in url
        assert "restrict_sr" not in url


# --- Post ID normalization tests ---


class TestPostIdNormalization:
    @patch("time.sleep")
    def test_bare_id(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("post_comments.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_post("abc123")

        assert "abc123" in str(captured[0].url)

    @patch("time.sleep")
    def test_fullname_prefix_stripped(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("post_comments.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_post("t3_abc123")

        url = str(captured[0].url)
        assert "abc123" in url
        assert "t3_" not in url

    @patch("time.sleep")
    def test_full_url_parsed(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("post_comments.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_post(
            "https://www.reddit.com/r/python/comments/abc123/some_title/"
        )

        url = str(captured[0].url)
        assert "abc123" in url


# --- Limit clamping tests ---


class TestLimitClamping:
    @patch("time.sleep")
    def test_zero_clamped_to_1(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("subreddit_listing.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_listing("python", "hot", limit=0)

        assert "limit=1" in str(captured[0].url)

    @patch("time.sleep")
    def test_negative_clamped_to_1(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("subreddit_listing.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_listing("python", "hot", limit=-5)

        assert "limit=1" in str(captured[0].url)

    @patch("time.sleep")
    def test_over_100_clamped_to_100(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("subreddit_listing.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_listing("python", "hot", limit=200)

        assert "limit=100" in str(captured[0].url)

    @patch("time.sleep")
    def test_search_limit_clamped(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("search_results.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.search("test", limit=0)

        assert "limit=1" in str(captured[0].url)


# --- Error handling tests ---


class TestErrorHandling:
    @patch("time.sleep")
    def test_404_raises_not_found(self, mock_sleep):
        from reddit_cli.client import RedditClient
        from reddit_cli.errors import ExitCode, RedditAPIError

        transport = httpx.MockTransport(
            lambda req: make_error_response(404, "Not Found")
        )
        client = RedditClient(_transport=transport)

        with pytest.raises(RedditAPIError) as exc_info:
            client.get_subreddit_info("nonexistent_sub_xyz")

        assert exc_info.value.exit_code == ExitCode.NOT_FOUND

    @patch("time.sleep")
    def test_403_raises_error(self, mock_sleep):
        from reddit_cli.client import RedditClient
        from reddit_cli.errors import ExitCode, RedditAPIError

        transport = httpx.MockTransport(
            lambda req: make_error_response(403, "Forbidden")
        )
        client = RedditClient(_transport=transport)

        with pytest.raises(RedditAPIError) as exc_info:
            client.get_subreddit_info("quarantined_sub")

        assert exc_info.value.exit_code == ExitCode.ERROR

    @patch("time.sleep")
    def test_429_retries_then_raises(self, mock_sleep):
        from reddit_cli.client import RedditClient
        from reddit_cli.errors import ExitCode, RedditAPIError

        call_count = 0

        def always_429(request):
            nonlocal call_count
            call_count += 1
            return make_error_response(429, "Too Many Requests")

        transport = httpx.MockTransport(always_429)
        client = RedditClient(_transport=transport)

        with pytest.raises(RedditAPIError) as exc_info:
            client.get_listing("python", "hot", limit=1)

        assert exc_info.value.exit_code == ExitCode.RATE_LIMITED
        # Should have retried at least once
        assert call_count >= 2

    @patch("time.sleep")
    def test_429_retry_succeeds(self, mock_sleep):
        from reddit_cli.client import RedditClient

        call_count = 0

        def retry_then_ok(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return make_error_response(429, "Too Many Requests")
            return make_response("subreddit_listing.json")

        transport = httpx.MockTransport(retry_then_ok)
        client = RedditClient(_transport=transport)
        listing = client.get_listing("python", "hot", limit=3)

        assert len(listing.posts) > 0
        assert call_count == 2


# --- Rate limiting tests ---


class TestRateLimiting:
    def test_respects_minimum_interval(self):
        from reddit_cli.client import RedditClient

        sleep_calls = []
        transport = httpx.MockTransport(
            lambda req: make_response("subreddit_listing.json")
        )
        client = RedditClient(_transport=transport)
        # Simulate a recent request by setting transport's last_request_time
        client._read_transport._last_request_time = time.time()

        with patch("reddit_cli.transports.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            client.get_listing("python", "hot", limit=1)

        # Should have triggered a sleep since we just set _last_request_time
        assert len(sleep_calls) > 0
        assert sleep_calls[0] > 0


# --- Quarantine access tests ---


class TestQuarantineAccess:
    @patch("time.sleep")
    def test_403_reports_quarantine_detail(self, mock_sleep):
        from reddit_cli.client import RedditClient
        from reddit_cli.errors import ExitCode, RedditAPIError

        transport = httpx.MockTransport(
            lambda req: make_error_response(403, "Forbidden")
        )
        client = RedditClient(_transport=transport)

        with pytest.raises(RedditAPIError) as exc_info:
            client.get_subreddit_info("theredpill")

        assert exc_info.value.exit_code == ExitCode.ERROR
        assert "quarantined" in exc_info.value.detail


# --- More children tests ---


class TestMoreChildren:
    @patch("time.sleep")
    def test_get_more_children_returns_comments(self, mock_sleep):
        from reddit_cli.client import RedditClient
        from reddit_cli.models import Comment

        transport = httpx.MockTransport(
            lambda req: make_response("morechildren.json")
        )
        client = RedditClient(_transport=transport)
        comments = client.get_more_children("t3_1s0gfyb", ["obt4j03", "obt308q"])

        assert len(comments) > 0
        assert all(isinstance(c, Comment) for c in comments)
        assert comments[0].author
        assert comments[0].body

    @patch("time.sleep")
    def test_get_more_children_url_params(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("morechildren.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        client.get_more_children("t3_abc123", ["id1", "id2", "id3"])

        url = str(captured[0].url)
        assert "/api/morechildren.json" in url
        assert "link_id=t3_abc123" in url
        assert "id1%2Cid2%2Cid3" in url or "id1,id2,id3" in url

    @patch("time.sleep")
    def test_get_more_children_batches_over_100(self, mock_sleep):
        from reddit_cli.client import RedditClient

        captured = []

        def capture(request):
            captured.append(request)
            return make_response("morechildren.json")

        transport = httpx.MockTransport(capture)
        client = RedditClient(_transport=transport)
        ids = [f"id{i}" for i in range(150)]
        client.get_more_children("t3_abc123", ids)

        # Should have made 2 requests: 100 + 50
        assert len(captured) == 2

    @patch("time.sleep")
    def test_get_post_expand_fetches_more(self, mock_sleep):
        from reddit_cli.client import RedditClient
        from reddit_cli.models import Comment

        call_count = 0

        def route(request):
            nonlocal call_count
            call_count += 1
            url = str(request.url)
            if "/api/morechildren" in url:
                return make_response("morechildren.json")
            return make_response("post_comments.json")

        transport = httpx.MockTransport(route)
        client = RedditClient(_transport=transport)
        detail = client.get_post("1s0gfyb", expand=True)

        # Should have made at least 2 requests (post + morechildren)
        assert call_count >= 2
        # All comments should be Comment objects (no raw dicts remaining)
        all_comments = detail.comments
        comment_count = sum(1 for c in all_comments if isinstance(c, Comment))
        assert comment_count > 0

    @patch("time.sleep")
    def test_get_post_no_expand_leaves_stubs(self, mock_sleep):
        from reddit_cli.client import RedditClient

        transport = httpx.MockTransport(
            lambda req: make_response("post_comments.json")
        )
        client = RedditClient(_transport=transport)
        detail = client.get_post("1s0gfyb", expand=False)

        # Should have raw dict stubs (the "more" items)
        has_stubs = any(isinstance(c, dict) for c in detail.comments)
        assert has_stubs
