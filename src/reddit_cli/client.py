import re
from typing import Any

import httpx

from reddit_cli.errors import ForbiddenError, RedditAPIError
from reddit_cli.models import (
    Comment,
    Listing,
    Post,
    PostDetail,
    SubredditInfo,
    UserInfo,
)


def resolve_fullname(id_or_index: str) -> str:
    """Resolve a bare ID to a fullname. Passes through existing fullnames and numeric indices."""
    if id_or_index.startswith(("t1_", "t3_", "t5_")):
        return id_or_index
    if id_or_index.isdigit():
        return id_or_index  # Numeric index — caller must resolve from cache
    return f"t3_{id_or_index}"

_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?reddit\.com/r/\w+/comments/(\w+)"
)


class RedditClient:
    def __init__(
        self,
        user_agent: str = "reddit-cli/0.1.0",
        _transport: httpx.BaseTransport | None = None,
    ):
        from reddit_cli.config import RuntimeConfig
        from reddit_cli.fingerprint import BrowserFingerprint
        from reddit_cli.session import SessionState
        from reddit_cli.transports import ReadTransport, WriteTransport

        # Load saved credentials if available
        cred = None
        try:
            from reddit_cli.auth import load_credential
            cred = load_credential()
        except Exception:
            pass

        # Build session state from credential
        if cred and cred.cookies:
            self._session = SessionState(
                cookies=dict(cred.cookies),
                source=cred.source,
                username=cred.username,
                modhash=cred.modhash,
            )
        else:
            self._session = SessionState()
        self._session.refresh_capabilities()

        config = RuntimeConfig()
        fingerprint = BrowserFingerprint.chrome133_mac()

        # Create transports
        self._read_transport = ReadTransport(
            self._session,
            config=config,
            fingerprint=fingerprint,
            request_delay=config.read_request_delay,
            _transport=_transport,
        )
        self._write_transport = WriteTransport(
            self._session,
            config=config,
            fingerprint=fingerprint,
            request_delay=config.write_request_delay,
            _transport=_transport,
        )

        # Keep reference for backward compat (tests check _client.is_closed)
        self._client = self._read_transport._http

    def __enter__(self) -> "RedditClient":
        return self

    def __exit__(self, *args: object) -> None:
        self._read_transport.close()
        self._write_transport.close()

    def _request(self, path: str, params: dict | None = None) -> dict:
        """Read request via ReadTransport."""
        return self._read_transport.request("GET", path, params=params)

    def _post(self, path: str, data: dict[str, Any]) -> dict:
        """Write request via WriteTransport."""
        return self._write_transport.request("POST", path, data=data)

    @staticmethod
    def _normalize_post_id(post_id: str) -> str:
        # Full URL
        match = _URL_PATTERN.search(post_id)
        if match:
            return match.group(1)
        # t3_ prefix
        if post_id.startswith("t3_"):
            return post_id[3:]
        return post_id

    def _parse_comments(self, children: list) -> list[Comment | dict]:
        results: list[Comment | dict] = []
        for child in children:
            if child["kind"] == "t1":
                data = child["data"]
                comment = Comment(
                    id=data["id"],
                    author=data.get("author", "[deleted]"),
                    body=data.get("body", ""),
                    score=data.get("score", 0),
                    created_utc=data.get("created_utc", 0.0),
                    permalink=data.get("permalink", ""),
                    depth=data.get("depth", 0),
                    is_submitter=data.get("is_submitter", False),
                    stickied=data.get("stickied", False),
                    edited=data.get("edited", False),
                    parent_id=data.get("parent_id", ""),
                    distinguished=data.get("distinguished"),
                )
                replies_data = data.get("replies")
                if isinstance(replies_data, dict):
                    comment.replies = [
                        c
                        for c in self._parse_comments(
                            replies_data["data"]["children"]
                        )
                        if isinstance(c, Comment)
                    ]
                results.append(comment)
            elif child["kind"] == "more":
                results.append(child["data"])
        return results

    @staticmethod
    def _clamp_limit(limit: int) -> int:
        return min(max(limit, 1), 100)

    def _parse_thing(self, thing: dict) -> Comment:
        """Parse a single t1 thing from morechildren response into a Comment."""
        data = thing["data"]
        return Comment(
            id=data["id"],
            author=data.get("author", "[deleted]"),
            body=data.get("body", ""),
            score=data.get("score", 0),
            created_utc=data.get("created_utc", 0.0),
            permalink=data.get("permalink", ""),
            depth=data.get("depth", 0),
            is_submitter=data.get("is_submitter", False),
            stickied=data.get("stickied", False),
            edited=data.get("edited", False),
            parent_id=data.get("parent_id", ""),
            distinguished=data.get("distinguished"),
        )

    def get_more_children(
        self, link_id: str, children_ids: list[str]
    ) -> list[Comment]:
        """Fetch expanded comments from /api/morechildren.json via read transport."""
        all_comments: list[Comment] = []
        for i in range(0, len(children_ids), 100):
            batch = children_ids[i : i + 100]
            try:
                data = self._request(
                    "/api/morechildren.json",
                    {
                        "api_type": "json",
                        "link_id": link_id,
                        "children": ",".join(batch),
                        "raw_json": 1,
                    },
                )
            except Exception:
                break
            things = data.get("json", {}).get("data", {}).get("things", [])
            for thing in things:
                if thing["kind"] == "t1":
                    all_comments.append(self._parse_thing(thing))
        return all_comments

    def get_listing(
        self,
        subreddit: str,
        sort: str,
        limit: int = 25,
        time: str = "day",
        after: str | None = None,
    ) -> Listing:
        params = {"limit": self._clamp_limit(limit), "raw_json": 1}
        if sort == "top":
            params["t"] = time
        if after:
            params["after"] = after

        data = self._request(f"/r/{subreddit}/{sort}.json", params)
        posts = [
            Post(**child["data"])
            for child in data["data"]["children"]
            if child["kind"] == "t3"
        ]
        return Listing(
            posts=posts,
            after=data["data"].get("after"),
            count=len(posts),
        )

    def get_subreddit_info(self, subreddit: str) -> SubredditInfo:
        try:
            data = self._request(f"/r/{subreddit}/about.json")
        except ForbiddenError as exc:
            raise RedditAPIError(
                message="Access denied",
                detail="Subreddit may be private or quarantined",
            ) from exc
        return SubredditInfo(**data["data"])

    def get_post(
        self,
        post_id: str,
        subreddit: str | None = None,
        limit: int = 10,
        depth: int = 3,
        expand: bool = False,
    ) -> PostDetail:
        pid = self._normalize_post_id(post_id)
        if subreddit:
            path = f"/r/{subreddit}/comments/{pid}.json"
        else:
            path = f"/comments/{pid}.json"

        data = self._request(path, {"limit": limit, "depth": depth, "raw_json": 1})
        post = Post(**data[0]["data"]["children"][0]["data"])
        comments = self._parse_comments(data[1]["data"]["children"])

        if expand:
            # Collect "more" stub IDs and expand them
            more_ids: list[str] = []
            real_comments: list[Comment | dict] = []
            for c in comments:
                if isinstance(c, dict) and "children" in c:
                    more_ids.extend(c["children"])
                else:
                    real_comments.append(c)
            if more_ids:
                link_id = f"t3_{pid}"
                expanded = self.get_more_children(link_id, more_ids)
                real_comments.extend(expanded)
            comments = real_comments

        return PostDetail(post=post, comments=comments)

    def get_user_info(self, username: str) -> UserInfo:
        data = self._request(f"/user/{username}/about.json")
        return UserInfo(**data["data"])

    def search(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "relevance",
        time: str = "all",
        limit: int = 25,
        after: str | None = None,
    ) -> Listing:
        params = {
            "q": query, "sort": sort, "t": time,
            "limit": self._clamp_limit(limit), "raw_json": 1,
        }
        if subreddit:
            path = f"/r/{subreddit}/search.json"
            params["restrict_sr"] = 1
        else:
            path = "/search.json"
        if after:
            params["after"] = after

        data = self._request(path, params)
        posts = [
            Post(**child["data"])
            for child in data["data"]["children"]
            if child["kind"] == "t3"
        ]
        return Listing(
            posts=posts,
            after=data["data"].get("after"),
            count=len(posts),
        )

    # ── Generic listing methods ────────────────────────────────────────

    def _get_generic_listing(
        self, path: str, limit: int = 25, after: str | None = None,
    ) -> Listing:
        params = {"limit": self._clamp_limit(limit), "raw_json": 1}
        if after:
            params["after"] = after
        data = self._request(path, params)
        posts = [
            Post(**child["data"])
            for child in data["data"]["children"]
            if child["kind"] == "t3"
        ]
        return Listing(posts=posts, after=data["data"].get("after"), count=len(posts))

    def get_popular(self, limit: int = 25, after: str | None = None) -> Listing:
        return self._get_generic_listing("/r/popular.json", limit, after)

    def get_all(self, limit: int = 25, after: str | None = None) -> Listing:
        return self._get_generic_listing("/r/all.json", limit, after)

    def get_home(self, limit: int = 25, after: str | None = None) -> Listing:
        return self._get_generic_listing("/.json", limit, after)

    def get_user_posts(self, username: str, limit: int = 25, after: str | None = None) -> Listing:
        return self._get_generic_listing(f"/user/{username}/submitted.json", limit, after)

    def get_user_comments(self, username: str, limit: int = 25, after: str | None = None) -> dict:
        params = {"limit": self._clamp_limit(limit), "raw_json": 1}
        if after:
            params["after"] = after
        return self._request(f"/user/{username}/comments.json", params)

    def get_me(self) -> UserInfo:
        """Get the authenticated user's profile."""
        data = self._request("/api/me.json")
        d = data.get("data", data)
        return UserInfo(**d)

    def get_saved(self, username: str, limit: int = 25, after: str | None = None) -> Listing:
        return self._get_generic_listing(f"/user/{username}/saved.json", limit, after)

    def get_upvoted(self, username: str, limit: int = 25, after: str | None = None) -> Listing:
        return self._get_generic_listing(f"/user/{username}/upvoted.json", limit, after)

    # ── Write methods ───────────────────────────────────────────────

    def vote(self, fullname: str, direction: int = 1) -> dict:
        return self._post("/api/vote", {"id": fullname, "dir": str(direction)})

    def save_item(self, fullname: str) -> dict:
        return self._post("/api/save", {"id": fullname})

    def unsave_item(self, fullname: str) -> dict:
        return self._post("/api/unsave", {"id": fullname})

    def subscribe(self, subreddit: str, action: str = "sub") -> dict:
        return self._post("/api/subscribe", {"sr_name": subreddit, "action": action})

    def post_comment(self, parent_fullname: str, text: str) -> dict:
        return self._post("/api/comment", {"parent": parent_fullname, "text": text})
