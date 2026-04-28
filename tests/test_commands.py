import json
from unittest.mock import patch

from typer.testing import CliRunner

from reddit_cli.models import (
    Comment,
    Listing,
    Post,
    PostDetail,
    SubredditInfo,
    UserInfo,
)

runner = CliRunner()


def make_post(**overrides) -> Post:
    defaults = dict(
        id="abc123",
        title="Test Post",
        author="testuser",
        subreddit="python",
        score=42,
        upvote_ratio=0.95,
        num_comments=10,
        created_utc=1774168543.0,
        permalink="/r/python/comments/abc123/test_post/",
        url="https://www.reddit.com/r/python/comments/abc123/test_post/",
        selftext="Hello world",
        is_self=True,
    )
    defaults.update(overrides)
    return Post(**defaults)


def make_listing(n: int = 3) -> Listing:
    posts = [make_post(id=f"post{i}", title=f"Post {i}") for i in range(n)]
    return Listing(posts=posts, after="cursor" if n > 0 else None, count=n)


def make_comment(**overrides) -> Comment:
    defaults = dict(
        id="com1",
        author="commenter",
        body="Great post!",
        score=5,
        created_utc=1774168543.0,
        permalink="/r/python/comments/abc123/test_post/com1/",
        depth=0,
        is_submitter=False,
        stickied=False,
        edited=False,
        parent_id="t3_abc123",
    )
    defaults.update(overrides)
    return Comment(**defaults)


def make_subreddit_info() -> SubredditInfo:
    return SubredditInfo(
        id="2qh0y",
        display_name="Python",
        title="Python",
        public_description="The Python community",
        subscribers=1463850,
        created_utc=1201230879.0,
    )


def make_user_info() -> UserInfo:
    return UserInfo(
        id="1w72",
        name="spez",
        created_utc=1118030400.0,
        total_karma=937136,
        is_employee=True,
        has_verified_email=True,
    )


# --- Sub commands ---


class TestSubHot:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.return_value = make_listing(2)

        result = runner.invoke(app, ["sub", "hot", "python"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert len(data["data"]["posts"]) == 2

    @patch("reddit_cli.client.RedditClient")
    def test_limit_flag(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.return_value = make_listing(5)

        result = runner.invoke(app, ["sub", "hot", "python", "--limit", "5"])
        assert result.exit_code == 0
        instance.get_listing.assert_called_once_with("python", "hot", limit=5, after=None)


class TestSubAfter:
    @patch("reddit_cli.client.RedditClient")
    def test_after_flag_passed_through(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.return_value = make_listing(1)

        result = runner.invoke(
            app, ["sub", "hot", "python", "--after", "t3_abc123"]
        )
        assert result.exit_code == 0
        instance.get_listing.assert_called_once_with(
            "python", "hot", limit=25, after="t3_abc123"
        )

    @patch("reddit_cli.client.RedditClient")
    def test_after_flag_on_top(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.return_value = make_listing(1)

        result = runner.invoke(
            app, ["sub", "top", "python", "--after", "t3_xyz", "--time", "week"]
        )
        assert result.exit_code == 0
        instance.get_listing.assert_called_once_with(
            "python", "top", limit=25, time="week", after="t3_xyz"
        )


class TestSubTop:
    @patch("reddit_cli.client.RedditClient")
    def test_time_flag(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.return_value = make_listing(1)

        result = runner.invoke(
            app, ["sub", "top", "python", "--time", "week", "--limit", "10"]
        )
        assert result.exit_code == 0
        instance.get_listing.assert_called_once_with(
            "python", "top", limit=10, time="week", after=None
        )


class TestSubNew:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.return_value = make_listing(1)

        result = runner.invoke(app, ["sub", "new", "python"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True


class TestSubRising:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.return_value = make_listing(1)

        result = runner.invoke(app, ["sub", "rising", "python"])
        assert result.exit_code == 0


class TestSubInfo:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_subreddit_info.return_value = make_subreddit_info()

        result = runner.invoke(app, ["sub", "info", "python"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["display_name"] == "Python"


# --- Post commands ---


class TestPostRead:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_post.return_value = PostDetail(
            post=make_post(), comments=[make_comment()]
        )

        result = runner.invoke(app, ["post", "read", "abc123"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["post"]["id"] == "abc123"
        assert len(data["data"]["comments"]) == 1

    @patch("reddit_cli.client.RedditClient")
    def test_limit_and_depth_flags(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_post.return_value = PostDetail(
            post=make_post(), comments=[]
        )

        result = runner.invoke(
            app, ["post", "read", "abc123", "--limit", "20", "--depth", "5"]
        )
        assert result.exit_code == 0
        instance.get_post.assert_called_once_with("abc123", limit=20, depth=5, expand=False)

    @patch("reddit_cli.client.RedditClient")
    def test_expand_flag(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_post.return_value = PostDetail(
            post=make_post(), comments=[make_comment()]
        )

        result = runner.invoke(
            app, ["post", "read", "abc123", "--expand"]
        )
        assert result.exit_code == 0
        instance.get_post.assert_called_once_with("abc123", limit=10, depth=3, expand=True)


# --- User commands ---


class TestUserInfo:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_user_info.return_value = make_user_info()

        result = runner.invoke(app, ["user", "info", "spez"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["name"] == "spez"


# --- Search command ---


class TestSearch:
    @patch("reddit_cli.client.RedditClient")
    def test_returns_json(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.search.return_value = make_listing(2)

        result = runner.invoke(app, ["search", "asyncio"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert len(data["data"]["posts"]) == 2

    @patch("reddit_cli.client.RedditClient")
    def test_subreddit_flag(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.search.return_value = make_listing(1)

        result = runner.invoke(
            app, ["search", "asyncio", "--subreddit", "python", "--sort", "top"]
        )
        assert result.exit_code == 0
        instance.search.assert_called_once_with(
            "asyncio", subreddit="python", sort="top", time="all", limit=25, after=None
        )

    @patch("reddit_cli.client.RedditClient")
    def test_after_flag(self, MockClient):
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.search.return_value = make_listing(1)

        result = runner.invoke(
            app, ["search", "asyncio", "--after", "t3_cursor"]
        )
        assert result.exit_code == 0
        instance.search.assert_called_once_with(
            "asyncio", subreddit=None, sort="relevance", time="all", limit=25, after="t3_cursor"
        )


# --- Error handling in commands ---


class TestCommandErrors:
    @patch("reddit_cli.client.RedditClient")
    def test_not_found_exits_3(self, MockClient):
        from reddit_cli.errors import ExitCode, RedditAPIError
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.side_effect = RedditAPIError(
            ExitCode.NOT_FOUND, "Not found"
        )

        result = runner.invoke(app, ["sub", "hot", "nonexistent_xyz"])
        assert result.exit_code == ExitCode.NOT_FOUND
        # Output contains JSON on stdout + error message on stderr (mixed by runner)
        # Extract just the JSON part
        json_str = result.output[: result.output.index("\n}") + 2]
        data = json.loads(json_str)
        assert data["ok"] is False

    @patch("reddit_cli.client.RedditClient")
    def test_rate_limited_exits_4(self, MockClient):
        from reddit_cli.errors import ExitCode, RedditAPIError
        from reddit_cli.main import app

        instance = MockClient.return_value
        instance.get_listing.side_effect = RedditAPIError(
            ExitCode.RATE_LIMITED, "Rate limited"
        )

        result = runner.invoke(app, ["sub", "hot", "python"])
        assert result.exit_code == ExitCode.RATE_LIMITED


# --- Help output ---


class TestHelp:
    def test_root_help(self):
        from reddit_cli.main import app

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "sub" in result.output
        assert "post" in result.output
        assert "user" in result.output
        assert "search" in result.output

    def test_sub_help(self):
        from reddit_cli.main import app

        result = runner.invoke(app, ["sub", "--help"])
        assert result.exit_code == 0
        assert "hot" in result.output
        assert "top" in result.output

    def test_post_help(self):
        from reddit_cli.main import app

        result = runner.invoke(app, ["post", "--help"])
        assert result.exit_code == 0
        assert "read" in result.output
