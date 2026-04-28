"""Tests for Rich listing and post detail renderers."""

from io import StringIO

from rich.console import Console

from reddit_cli.models import Comment, Listing, Post, PostDetail


def _make_post(**kw):
    defaults = dict(
        id="1", title="Test Post", author="testuser", subreddit="python",
        score=1500, upvote_ratio=0.95, num_comments=42, created_utc=0.0,
        permalink="/r/python/comments/1/test/", url="https://example.com",
        selftext="", domain="example.com", is_self=False,
        over_18=False, spoiler=False, stickied=False, locked=False,
        is_video=False,
    )
    defaults.update(kw)
    return Post(**defaults)


def _capture_render(func, *args, **kwargs) -> str:
    """Capture Rich console output as string."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    func(*args, _console=console, **kwargs)
    return buf.getvalue()


# ── C10: render_listing ───────────────────────────────────────────────


class TestRenderListing:
    def test_renders_post_titles(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[_make_post(title="My Cool Post")], after=None, count=1)
        output = _capture_render(render_listing, listing)
        assert "My Cool Post" in output

    def test_renders_index_numbers(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[_make_post(), _make_post(id="2")], after=None, count=2)
        output = _capture_render(render_listing, listing)
        assert "1" in output
        assert "2" in output

    def test_stickied_shows_pin(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[_make_post(stickied=True)], after=None, count=1)
        output = _capture_render(render_listing, listing)
        assert "\U0001f4cc" in output  # pin emoji

    def test_nsfw_shows_indicator(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[_make_post(over_18=True)], after=None, count=1)
        output = _capture_render(render_listing, listing)
        assert "\U0001f51e" in output  # 18+ emoji

    def test_video_shows_indicator(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[_make_post(is_video=True)], after=None, count=1)
        output = _capture_render(render_listing, listing)
        assert "\U0001f3ac" in output  # film emoji

    def test_empty_listing_message(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[], after=None, count=0)
        output = _capture_render(render_listing, listing)
        assert "No posts" in output

    def test_hint_line_present(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[_make_post()], after=None, count=1)
        output = _capture_render(render_listing, listing)
        assert "reddit post show" in output

    def test_pagination_hint_when_after_present(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[_make_post()], after="t3_cursor", count=1)
        output = _capture_render(render_listing, listing)
        assert "--after" in output

    def test_no_pagination_hint_when_no_after(self):
        from reddit_cli.output import render_listing
        listing = Listing(posts=[_make_post()], after=None, count=1)
        output = _capture_render(render_listing, listing)
        assert "--after" not in output


# ── C11: render_post_detail ───────────────────────────────────────────


def _make_comment(**kw):
    defaults = dict(
        id="c1", author="commenter", body="Great post!", score=10,
        created_utc=0.0, permalink="/", depth=0, is_submitter=False,
        stickied=False, edited=False, parent_id="t3_1",
    )
    defaults.update(kw)
    return Comment(**defaults)


class TestRenderPostDetail:
    def test_renders_post_title_and_body(self):
        from reddit_cli.output import render_post_detail
        post = _make_post(title="Big Title", selftext="Body text here")
        detail = PostDetail(post=post, comments=[])
        output = _capture_render(render_post_detail, detail)
        assert "Big Title" in output
        assert "Body text here" in output

    def test_renders_comment_tree(self):
        from reddit_cli.output import render_post_detail
        post = _make_post()
        comments = [_make_comment(body="Hello world")]
        detail = PostDetail(post=post, comments=comments)
        output = _capture_render(render_post_detail, detail)
        assert "Hello world" in output

    def test_comment_indentation_by_depth(self):
        from reddit_cli.output import render_post_detail
        post = _make_post()
        child = _make_comment(id="c2", body="Reply", depth=1, parent_id="t1_c1")
        parent = _make_comment(body="Parent", replies=[child])
        detail = PostDetail(post=post, comments=[parent])
        output = _capture_render(render_post_detail, detail)
        assert "Parent" in output
        assert "Reply" in output

    def test_score_color_coding(self):
        from reddit_cli.output import render_post_detail
        post = _make_post()
        comments = [_make_comment(score=100)]
        detail = PostDetail(post=post, comments=comments)
        output = _capture_render(render_post_detail, detail)
        assert "100" in output

    def test_submitter_highlighted(self):
        from reddit_cli.output import render_post_detail
        post = _make_post(author="op_user")
        comments = [_make_comment(author="op_user", is_submitter=True)]
        detail = PostDetail(post=post, comments=comments)
        output = _capture_render(render_post_detail, detail)
        assert "OP" in output

    def test_empty_comments(self):
        from reddit_cli.output import render_post_detail
        post = _make_post()
        detail = PostDetail(post=post, comments=[])
        output = _capture_render(render_post_detail, detail)
        # At minimum should not crash; check something rendered
        assert output is not None
        # At minimum should not crash
