# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (Python 3.10+; uv picks a compatible interpreter)
uv venv
uv pip install -e ".[dev]"

# Run all tests
uv run pytest tests/ -v

# Run a single test file
uv run pytest tests/test_client.py -v

# Run a specific test
uv run pytest tests/test_commands.py::TestSubHot::test_returns_json -v

# Lint (check)
uv run ruff check src/ tests/

# Lint (auto-fix)
uv run ruff check --fix src/ tests/

# Run the CLI
uv run reddit sub hot python --limit 5
uv run reddit --help
```

If you don't have `uv`, you can use the venv directly: `.venv/bin/python -m pytest …` on macOS/Linux, `.venv/Scripts/python -m pytest …` on Windows.

**Always lint before committing.** Run `uv run ruff check src/ tests/` and fix any errors before creating a commit.

Set `PYTHONIOENCODING=utf-8` when piping output on Windows.

## Architecture

The CLI follows a layered pipeline: **Typer commands -> handle_command() -> RedditClient -> ReadTransport/WriteTransport -> Reddit .json endpoints -> Pydantic models -> TTY-aware output**.

### Core Layers

- **`main.py`** wires sub-apps (`auth`, `sub`, `post`, `user`) and top-level commands (`search`, `vote`, `save`, `subscribe`, `comment`, `popular`, `all`, `feed`, `open`, `saved`, `upvoted`, `export`).
- **`commands/helpers.py`** — `handle_command()` orchestrator eliminates try/except duplication. Also `require_auth()`, `optional_auth()` for auth gating.
- **`commands/`** are thin wrappers — each lazily imports `RedditClient` inside action lambdas (for startup speed), delegates to `handle_command()`.
- **`client.py`** wraps `ReadTransport`/`WriteTransport`. Context manager (`with RedditClient() as client:`). Has read methods (`get_listing`, `get_post`, `get_subreddit_info`, `search`, `get_user_info`, `get_popular`, `get_all`, `get_home`, `get_user_posts`, `get_user_comments`, `get_me`, `get_saved`, `get_upvoted`) and write methods (`vote`, `save_item`, `unsave_item`, `subscribe`, `post_comment`).
- **`models.py`** uses Pydantic `BaseModel` with `extra="ignore"` to parse Reddit's 90+ field responses into clean models.
- **`output.py`** — `OutputContext` dataclass + `emit()` for TTY-aware routing: Rich tables in terminal, JSON/YAML envelope for pipes/agents. `render_listing()` and `render_post_detail()` for Rich output. `exit_for_error()` for dual-mode error output.
- **`errors.py`** defines exception hierarchy (`NotFoundError`, `RateLimitError`, `ForbiddenError`, `AuthRequiredError`, `SessionExpiredError`) and `error_code_for_exception()` for string error codes.

### Transport Layer

- **`transports.py`** — `ReadTransport`/`WriteTransport` with Gaussian jitter, exponential backoff, response cookie merging, HTML detection, modhash injection. Integrated into `RedditClient` constructor.
- **`session.py`** — `SessionState` with capability detection (`is_authenticated`, `can_write`). Built from `Credential` in client constructor.
- **`fingerprint.py`** — `BrowserFingerprint` Pydantic model, Chrome 133 macOS identity.
- **`config.py`** — `RuntimeConfig` frozen Pydantic model (timeout=30s, read_delay=1s, write_delay=2.5s, max_retries=3).

### Auth

- **`auth.py`** — `Credential` model, browser cookie extraction via `browser-cookie3`, TTL-based refresh (7 days). Warns on stderr when falling back to stale cookies.
- **`index_cache.py`** — Short-index cache + `resolve_fullname_from_index()` for consolidated index/ID/fullname resolution.
- **`constants.py`** — URLs, Chrome 133 headers, sort/time enums.

### Comment expansion

`_parse_comments()` handles Reddit's polymorphic `replies` field (empty string or nested Listing dict). `get_more_children()` uses the read transport to batch-fetch collapsed comment stubs via `/api/morechildren.json`.

## Testing Patterns

TDD approach. Each layer has its own test file with fixtures from real Reddit API responses in `tests/fixtures/`.

- **Client tests** use `httpx.MockTransport` injected via `RedditClient(_transport=mock)`. Patch `reddit_cli.transports.time.sleep` to avoid delays. Patch `reddit_cli.auth.load_credential` to control session state.
- **Command tests** use `typer.testing.CliRunner` with `@patch("reddit_cli.client.RedditClient")` (patched at definition site since commands use lazy imports).
- **Transport tests** patch `reddit_cli.transports.time.sleep` (module-level, not global, to avoid breaking httpx cookie internals).
- **Output routing tests** use `capsys` and `Console(file=StringIO())` for Rich rendering.

## Key Design Decisions

- Python >=3.10 with modern type hints (`str | None`, `list[X]`).
- Lazy imports in all command files — `httpx` not loaded until a command actually runs. Verified by `test_startup.py`.
- TTY-aware output: Rich tables in terminal, JSON envelope for pipes (agent-friendly default).
- `_clamp_limit()` constrains limit to [1, 100].
- `resolve_fullname_from_index()` consolidates bare ID, `t3_` prefix, and numeric index resolution.
- `save_index()` called after every listing command for `reddit post show <N>` navigation.
- All commands support `--json`, `--yaml`, `--compact` flags.

## Release Pipeline

- Pushing a tag matching `v*` triggers `.github/workflows/release.yml`. It builds Nuitka one-file binaries on linux-x64 (ubuntu-22.04), windows-x64 (windows-latest), and macos-arm64 (macos-15), then publishes a GitHub release on **both** `leog25/reddit-cli` (default `GITHUB_TOKEN`) and `leog25/reddit-cli-releases` (cross-repo `RELEASES_PAT` secret).
- The companion repo `leog25/reddit-cli-releases` is the canonical install source — `install.sh` and `install.ps1` (mirrored at the root of this repo and at the root of the releases repo) hardcode `leog25/reddit-cli-releases` and default to resolving `/releases/latest` via the GitHub API.
- `.github/workflows/release-only.yml` is a manual `workflow_dispatch` fallback that re-publishes from a previous run's artifacts to the source repo only — useful when a tag ran but the cross-repo upload failed.
- Release-related files at the repo root: `build.py` (Nuitka driver), `install.sh`, `install.ps1`. `SKILL.md` is a Claude Code skill manifest pointing at the public install URLs.
