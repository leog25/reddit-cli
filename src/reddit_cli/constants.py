"""Constants — API endpoints, headers, and config paths."""

from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".config" / "reddit-cli"
CREDENTIAL_FILE = CONFIG_DIR / "credential.json"
INDEX_CACHE_FILE = CONFIG_DIR / "index_cache.json"

# ── Base URL ────────────────────────────────────────────────────────
BASE_URL = "https://www.reddit.com"

# ── Listing endpoints (GET, append .json) ───────────────────────────
HOME_URL = "/.json"
POPULAR_URL = "/r/popular.json"
ALL_URL = "/r/all.json"
SUBREDDIT_URL = "/r/{subreddit}/{sort}.json"
SUBREDDIT_ABOUT_URL = "/r/{subreddit}/about.json"

# ── Post / comments ────────────────────────────────────────────────
POST_COMMENTS_URL = "/r/{subreddit}/comments/{post_id}.json"
POST_COMMENTS_SHORT_URL = "/comments/{post_id}.json"
MORECHILDREN_URL = "/api/morechildren.json"

# ── Search ──────────────────────────────────────────────────────────
SEARCH_URL = "/search.json"
SUBREDDIT_SEARCH_URL = "/r/{subreddit}/search.json"

# ── User ────────────────────────────────────────────────────────────
USER_ABOUT_URL = "/user/{username}/about.json"
USER_POSTS_URL = "/user/{username}/submitted.json"
USER_COMMENTS_URL = "/user/{username}/comments.json"
USER_SAVED_URL = "/user/{username}/saved.json"
USER_UPVOTED_URL = "/user/{username}/upvoted.json"

# ── Auth / identity ────────────────────────────────────────────────
ME_URL = "/api/v1/me"
SUBSCRIPTIONS_URL = "/subreddits/mine/subscriber.json"

# ── Write actions (POST) ───────────────────────────────────────────
VOTE_URL = "/api/vote"
SAVE_URL = "/api/save"
UNSAVE_URL = "/api/unsave"
SUBSCRIBE_URL = "/api/subscribe"
COMMENT_URL = "/api/comment"

# ── Request Headers (Chrome 133, macOS) ────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    ),
    "sec-ch-ua": '"Chromium";v="133", "Not(A:Brand";v="99", "Google Chrome";v="133"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Cookie keys required for authenticated sessions ────────────────
REQUIRED_COOKIES = {"reddit_session"}

# ── Sort / filter options ──────────────────────────────────────────
SORT_OPTIONS = ["hot", "new", "top", "rising", "controversial", "best"]
TIME_FILTERS = ["hour", "day", "week", "month", "year", "all"]
SEARCH_SORT_OPTIONS = ["relevance", "hot", "top", "new", "comments"]

# ── Limits ──────────────────────────────────────────────────────────
DEFAULT_LIMIT = 25
MAX_LIMIT = 100
