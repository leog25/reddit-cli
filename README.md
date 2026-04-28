# reddit-cli

CLI for AI agents to interact with Reddit. Browse subreddits, read posts and comments, search, vote, save, subscribe, comment, and run batch Python scripts against a shared `RedditClient`. Output is TTY-aware: Rich tables in your terminal, JSON envelopes when piped — agent-friendly by default.

No API key required for reads. Browser cookies for writes.

## Install

**macOS / Linux**
```bash
curl -fsSL https://raw.githubusercontent.com/leog25/reddit-cli-releases/main/install.sh | bash
```

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/leog25/reddit-cli-releases/main/install.ps1 | iex
```

**From source**
```bash
uv venv --python 3.12
uv pip install -e .
```

## Quick start

```bash
reddit sub hot python --limit 5
reddit search "async runtime" --subreddit rust --sort top --time year
reddit post show 1 --expand                       # read post #1 from the last listing
reddit auth login                                 # extract cookies from your browser
reddit vote 1                                     # upvote post #1
```

## Features

- Read endpoints: `sub hot|new|top|rising`, `popular`, `all`, `feed`, `search`, `post read|show`, `user info|posts|comments`, `sub info`
- Write endpoints (auth required): `vote`, `save`, `subscribe`, `comment`
- Authenticated browsing: `saved`, `upvoted`, `auth whoami`
- Batch scripting: `reddit exec` runs a Python script with a pre-initialized `RedditClient` (single process, shared session)
- Export: `reddit export` dumps search results to JSON or CSV
- Index navigation: every listing populates an index, so `reddit post show 3` reads the third post from the last listing
- Rate-limited with Gaussian jitter and exponential backoff on 429s

## Output

All listing and read commands accept `--json`, `--yaml`, and `--compact`. The envelope:

```json
{"ok": true,  "schema_version": "1", "data": {...}}
{"ok": false, "schema_version": "1", "error": {"code": "not_found", "message": "..."}}
```

Error codes: `not_found`, `rate_limited`, `forbidden`, `not_authenticated`, `api_error`, `script_error`, `timeout`, `file_not_found`.

In a terminal you get Rich tables. When piped, you get the JSON envelope.

## Auth

Writes require browser cookies. `reddit auth login` extracts them from your local Chrome/Firefox/etc. via `browser-cookie3`. If that fails (common on Windows without admin), use `reddit auth set-cookie <value>` and paste your `reddit_session` cookie manually — DevTools → Application → Cookies → `https://www.reddit.com`.

## Development

See [CLAUDE.md](CLAUDE.md) for the full command list — install with `uv pip install -e ".[dev]"`, then `pytest tests/ -v` and `ruff check src/ tests/`.

## License

MIT — see [LICENSE](LICENSE).
