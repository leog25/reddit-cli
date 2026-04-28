import json

from reddit_cli.models import Listing, Post, SubredditInfo, UserInfo


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
    posts = [make_post(id=f"post{i}", title=f"Post {i}", score=i * 10) for i in range(n)]
    return Listing(posts=posts, after="cursor_xyz" if n > 0 else None, count=n)


class TestOutputJson:
    def test_success_envelope(self, capsys):
        from reddit_cli.output import output_json

        listing = make_listing(2)
        output_json(listing)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert "data" in data
        assert len(data["data"]["posts"]) == 2

    def test_envelope_is_valid_json(self, capsys):
        from reddit_cli.output import output_json

        post = make_post()
        output_json(post)

        captured = capsys.readouterr()
        # Should parse without error
        data = json.loads(captured.out)
        assert isinstance(data, dict)

    def test_nothing_on_stderr(self, capsys):
        from reddit_cli.output import output_json

        output_json(make_post())
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_subreddit_info_output(self, capsys):
        from reddit_cli.output import output_json

        info = SubredditInfo(
            id="2qh0y",
            display_name="Python",
            title="Python",
            subscribers=1463850,
            created_utc=1201230879.0,
        )
        output_json(info)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert data["data"]["display_name"] == "Python"

    def test_user_info_output(self, capsys):
        from reddit_cli.output import output_json

        user = UserInfo(
            id="1w72",
            name="spez",
            created_utc=1118030400.0,
            total_karma=937136,
        )
        output_json(user)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["data"]["name"] == "spez"


class TestOutputError:
    def test_error_envelope(self, capsys):
        from reddit_cli.output import output_error

        output_error(3, "Not found")

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is False
        assert data["error"]["code"] == "3"
        assert data["error"]["message"] == "Not found"

    def test_error_with_detail(self, capsys):
        from reddit_cli.output import output_error

        output_error(4, "Rate limited", detail="Retry after 60s")

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"]["detail"] == "Retry after 60s"

    def test_error_message_on_stderr(self, capsys):
        from reddit_cli.output import output_error

        output_error(1, "Connection failed")

        captured = capsys.readouterr()
        assert "Connection failed" in captured.err


class TestOutputTable:
    def test_table_output_contains_post_data(self, capsys):
        from reddit_cli.output import output_table_posts

        listing = make_listing(2)
        output_table_posts(listing)

        captured = capsys.readouterr()
        # Table output should contain post titles
        assert "Post 0" in captured.out
        assert "Post 1" in captured.out

    def test_table_output_contains_scores(self, capsys):
        from reddit_cli.output import output_table_posts

        listing = make_listing(2)
        output_table_posts(listing)

        captured = capsys.readouterr()
        # Scores should appear
        assert "0" in captured.out
        assert "10" in captured.out

    def test_empty_listing_table(self, capsys):
        from reddit_cli.output import output_table_posts

        listing = make_listing(0)
        output_table_posts(listing)

        captured = capsys.readouterr()
        # Should still produce output (table headers at minimum)
        assert len(captured.out) > 0
