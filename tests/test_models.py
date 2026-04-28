import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


# --- Post model tests ---


class TestPost:
    def setup_method(self):
        data = load_fixture("subreddit_listing.json")
        self.raw_post = data["data"]["children"][0]["data"]

    def test_parse_post_from_fixture(self):
        from reddit_cli.models import Post

        post = Post(**self.raw_post)
        assert post.id == self.raw_post["id"]
        assert post.title == self.raw_post["title"]
        assert post.author == self.raw_post["author"]
        assert post.subreddit == self.raw_post["subreddit"]
        assert isinstance(post.score, int)
        assert isinstance(post.upvote_ratio, float)
        assert isinstance(post.num_comments, int)
        assert isinstance(post.created_utc, float)
        assert post.permalink.startswith("/r/")
        assert isinstance(post.is_self, bool)
        assert isinstance(post.over_18, bool)

    def test_extra_fields_ignored(self):
        from reddit_cli.models import Post

        post = Post(**self.raw_post)
        dumped = post.model_dump()
        # Reddit returns 90+ fields, we should have far fewer
        assert len(dumped) < 30
        # These reddit-internal fields should not be present
        assert "gilded" not in dumped
        assert "all_awardings" not in dumped
        assert "pwls" not in dumped

    def test_optional_link_flair_text(self):
        from reddit_cli.models import Post

        # With flair
        post_with_flair = Post(**self.raw_post)
        # link_flair_text can be str or None, both valid
        assert post_with_flair.link_flair_text is None or isinstance(
            post_with_flair.link_flair_text, str
        )

        # Without flair (simulate None)
        data = dict(self.raw_post, link_flair_text=None)
        post_no_flair = Post(**data)
        assert post_no_flair.link_flair_text is None

    def test_selftext_empty_for_link_posts(self):
        from reddit_cli.models import Post

        data = dict(self.raw_post, is_self=False, selftext="")
        post = Post(**data)
        assert post.selftext == ""
        assert post.is_self is False

    def test_model_dump_serializes_to_json(self):
        from reddit_cli.models import Post

        post = Post(**self.raw_post)
        dumped = post.model_dump(mode="json")
        # Should be JSON-serializable
        json_str = json.dumps(dumped)
        assert isinstance(json_str, str)

    def test_parse_all_posts_in_listing(self):
        from reddit_cli.models import Post

        data = load_fixture("subreddit_listing.json")
        children = data["data"]["children"]
        for child in children:
            assert child["kind"] == "t3"
            post = Post(**child["data"])
            assert post.id
            assert post.title


# --- Comment model tests ---


class TestComment:
    def setup_method(self):
        data = load_fixture("post_comments.json")
        self.post_data = data[0]["data"]["children"][0]["data"]
        self.comments_data = data[1]["data"]["children"]

    def test_parse_comment(self):
        from reddit_cli.models import Comment

        raw = self.comments_data[0]["data"]
        comment = Comment(
            id=raw["id"],
            author=raw.get("author", "[deleted]"),
            body=raw.get("body", ""),
            score=raw.get("score", 0),
            created_utc=raw["created_utc"],
            permalink=raw.get("permalink", ""),
            depth=raw.get("depth", 0),
            is_submitter=raw.get("is_submitter", False),
            stickied=raw.get("stickied", False),
            edited=raw.get("edited", False),
            parent_id=raw["parent_id"],
            distinguished=raw.get("distinguished"),
        )
        assert comment.id == raw["id"]
        assert comment.author == raw["author"]
        assert isinstance(comment.body, str)
        assert isinstance(comment.score, int)
        assert isinstance(comment.depth, int)

    def test_edited_false(self):
        from reddit_cli.models import Comment

        raw = self.comments_data[0]["data"]
        comment = Comment(
            id=raw["id"],
            author=raw["author"],
            body=raw["body"],
            score=raw["score"],
            created_utc=raw["created_utc"],
            permalink=raw.get("permalink", ""),
            depth=raw["depth"],
            is_submitter=raw["is_submitter"],
            stickied=raw["stickied"],
            edited=False,
            parent_id=raw["parent_id"],
        )
        assert comment.edited is False

    def test_edited_timestamp(self):
        from reddit_cli.models import Comment

        raw = self.comments_data[0]["data"]
        comment = Comment(
            id=raw["id"],
            author=raw["author"],
            body=raw["body"],
            score=raw["score"],
            created_utc=raw["created_utc"],
            permalink=raw.get("permalink", ""),
            depth=raw["depth"],
            is_submitter=raw["is_submitter"],
            stickied=raw["stickied"],
            edited=1774200000.0,
            parent_id=raw["parent_id"],
        )
        assert isinstance(comment.edited, float)

    def test_deleted_author(self):
        from reddit_cli.models import Comment

        raw = dict(
            self.comments_data[0]["data"],
            author="[deleted]",
            body="[removed]",
        )
        comment = Comment(
            id=raw["id"],
            author=raw["author"],
            body=raw["body"],
            score=0,
            created_utc=raw["created_utc"],
            permalink=raw.get("permalink", ""),
            depth=0,
            is_submitter=False,
            stickied=False,
            edited=False,
            parent_id=raw["parent_id"],
        )
        assert comment.author == "[deleted]"
        assert comment.body == "[removed]"

    def test_replies_default_empty(self):
        from reddit_cli.models import Comment

        raw = self.comments_data[0]["data"]
        comment = Comment(
            id=raw["id"],
            author=raw["author"],
            body=raw["body"],
            score=raw["score"],
            created_utc=raw["created_utc"],
            permalink=raw.get("permalink", ""),
            depth=raw["depth"],
            is_submitter=raw["is_submitter"],
            stickied=raw["stickied"],
            edited=raw.get("edited", False),
            parent_id=raw["parent_id"],
        )
        assert comment.replies == []


# --- SubredditInfo model tests ---


class TestSubredditInfo:
    def setup_method(self):
        data = load_fixture("subreddit_about.json")
        self.raw = data["data"]

    def test_parse_subreddit_info(self):
        from reddit_cli.models import SubredditInfo

        info = SubredditInfo(**self.raw)
        assert info.display_name == "Python"
        assert info.title == "Python"
        assert isinstance(info.subscribers, int)
        assert info.subscribers > 0
        assert isinstance(info.created_utc, float)
        assert info.over18 is False
        assert info.subreddit_type == "public"
        assert info.quarantine is False

    def test_extra_fields_ignored(self):
        from reddit_cli.models import SubredditInfo

        info = SubredditInfo(**self.raw)
        dumped = info.model_dump()
        assert "header_img" not in dumped
        assert "icon_img" not in dumped


# --- UserInfo model tests ---


class TestUserInfo:
    def setup_method(self):
        data = load_fixture("user_about.json")
        self.raw = data["data"]

    def test_parse_user_info(self):
        from reddit_cli.models import UserInfo

        user = UserInfo(**self.raw)
        assert user.name == "spez"
        assert isinstance(user.total_karma, int)
        assert user.total_karma > 0
        assert isinstance(user.created_utc, float)
        assert user.is_employee is True
        assert user.has_verified_email is True

    def test_extra_fields_ignored(self):
        from reddit_cli.models import UserInfo

        user = UserInfo(**self.raw)
        dumped = user.model_dump()
        assert "subreddit" not in dumped
        assert "snoovatar_img" not in dumped


# --- Listing model tests ---


class TestListing:
    def test_parse_listing(self):
        from reddit_cli.models import Listing, Post

        data = load_fixture("subreddit_listing.json")
        posts = [Post(**child["data"]) for child in data["data"]["children"]]
        listing = Listing(
            posts=posts,
            after=data["data"]["after"],
            count=len(posts),
        )
        assert len(listing.posts) > 0
        assert listing.count == len(listing.posts)
        # after can be None or a string cursor
        assert listing.after is None or isinstance(listing.after, str)

    def test_empty_listing(self):
        from reddit_cli.models import Listing

        listing = Listing(posts=[], after=None, count=0)
        assert listing.posts == []
        assert listing.after is None
        assert listing.count == 0


# --- PostDetail model tests ---


class TestPostDetail:
    def test_parse_post_detail(self):
        from reddit_cli.models import Post, PostDetail

        data = load_fixture("post_comments.json")
        post = Post(**data[0]["data"]["children"][0]["data"])
        detail = PostDetail(post=post, comments=[])
        assert detail.post.id == post.id
        assert detail.comments == []


# --- CLIError model tests ---


class TestCLIError:
    def test_create_error(self):
        from reddit_cli.models import CLIError

        err = CLIError(code=3, message="Not found")
        assert err.code == 3
        assert err.message == "Not found"
        assert err.detail is None

    def test_create_error_with_detail(self):
        from reddit_cli.models import CLIError

        err = CLIError(code=4, message="Rate limited", detail="Retry after 60s")
        assert err.detail == "Retry after 60s"

    def test_error_serializes(self):
        from reddit_cli.models import CLIError

        err = CLIError(code=1, message="Connection error")
        dumped = err.model_dump(mode="json")
        assert json.dumps(dumped)  # must be JSON-serializable
