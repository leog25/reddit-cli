---
name: reddit
description: Browse subreddits, read posts and comments, search Reddit, look up users, vote, save, subscribe, comment, export data, and run batch scripts via CLI. Supports --json/--yaml/--compact output flags. Triggers when tasks involve Reddit content, subreddit research, or community discussions. No API key required for reads; browser auth for writes.
argument-hint: "[command] [args]"
allowed-tools: Bash
---

Execute the `reddit` CLI to fulfill the user's request about: $ARGUMENTS


**Important**: If `reddit` is not found, install it first:
- macOS/Linux: `curl -fsSL https://raw.githubusercontent.com/leog25/reddit-cli-releases/main/install.sh | bash`
- Windows: `irm https://raw.githubusercontent.com/leog25/reddit-cli-releases/main/install.ps1 | iex`

## Output Format

All commands return JSON to stdout:
```json
{"ok": true, "schema_version": "1", "data": {...}}
{"ok": false, "schema_version": "1", "error": {"code": "not_found", "message": "..."}}
```

Error codes: `not_found`, `rate_limited`, `forbidden`, `not_authenticated`, `api_error`, `script_error`, `timeout`, `file_not_found`.

Always parse the JSON response, check `ok` is `true`, then extract and present the relevant information. On failure, report the error message and suggest a fix.

## Output Format Flags

All listing and read commands support these flags:
- `--json` — Force JSON envelope output (default for pipes/agents)
- `--yaml` — Force YAML envelope output
- `--compact` — Strip non-essential fields (agent-friendly, fewer tokens)

When running in a terminal (TTY), output defaults to Rich tables. When piped, defaults to JSON.

## Read Commands (no auth required)

### Browse posts
```bash
reddit sub hot <subreddit> [--limit N] [--after CURSOR] [--json|--yaml|--compact]
reddit sub new <subreddit> [--limit N] [--after CURSOR] [--json|--yaml|--compact]
reddit sub top <subreddit> [--limit N] [--time hour|day|week|month|year|all] [--after CURSOR]
reddit sub rising <subreddit> [--limit N] [--after CURSOR] [--json|--yaml|--compact]
reddit popular [--limit N] [--after CURSOR] [--json|--yaml|--compact]
reddit all [--limit N] [--after CURSOR] [--json|--yaml|--compact]
reddit feed [--limit N] [--after CURSOR] [--json|--yaml|--compact]
```

### Subreddit/user info
```bash
reddit sub info <subreddit>
reddit user info <username>
reddit user posts <username> [--limit N]
reddit user comments <username> [--limit N]
```

### Read post + comments
```bash
reddit post read <post_id> [--limit N] [--depth D] [--expand] [--json|--yaml]
reddit post show <index> [--limit N] [--depth D] [--expand] [--json|--yaml]
```
`post_id` accepts a bare ID, `t3_` fullname, or full Reddit URL. Use `--expand` to fetch all collapsed "load more" comments.

`show` reads by index number from the last listing.

### Search + Export
```bash
reddit search "<query>" [--subreddit NAME] [--sort relevance|hot|top|new|comments] [--time all|hour|day|week|month|year] [--limit N] [--json|--yaml|--compact]
reddit export "<query>" [--subreddit NAME] [--count N] [--output FILE] [--format json|csv]
```

## Write Commands (require auth)

First authenticate: `reddit auth login` (extracts cookies from your browser).

```bash
reddit vote <id_or_index> [--down] [--undo]
reddit save <id_or_index> [--undo]
reddit subscribe <subreddit> [--undo]
reddit comment <id_or_index> "<text>"
```

### Authenticated browsing (require auth)
```bash
reddit saved [--limit N] [--after CURSOR] [--json|--yaml|--compact]     # Your saved posts
reddit upvoted [--limit N] [--after CURSOR] [--json|--yaml|--compact]   # Your upvoted posts
reddit auth whoami                                                       # Current user profile
```

## Auth Commands
```bash
reddit auth login                   # Extract cookies from browser (needs admin on Windows)
reddit auth set-cookie <value>      # Manually set reddit_session cookie (recommended on Windows)
reddit auth logout                  # Clear saved credentials
reddit auth status                  # Check auth status
reddit auth whoami                  # Show authenticated user's profile
```

To get the cookie value: open Chrome DevTools (F12) > Application > Cookies > `https://www.reddit.com` > copy `reddit_session` value.

## Batch Scripting (exec)

Run a Python script with a pre-initialized `RedditClient` — single process, shared session, one credential load. Ideal for multi-step scraping and bulk operations.

```bash
reddit exec -c "<python code>"        # Inline code
reddit exec script.py                 # Run a file
reddit exec -                         # Read from stdin
reddit exec -c "..." --timeout 300    # Custom timeout (default 120s)
```

### Pre-populated namespace

| Name | Type | Description |
|------|------|-------------|
| `client` | `RedditClient` | Shared session (context-managed) |
| `result` | `list` | Accumulator — contents become the JSON output |
| `Post`, `Comment`, `Listing`, `PostDetail`, `SubredditInfo`, `UserInfo` | models | Pydantic models for type-aware scripting |
| `sleep` | `function` | `time.sleep` for manual rate control |

### Example: scrape multiple subreddits
```bash
reddit exec -c "
for sub in ['python', 'rust', 'golang']:
    listing = client.get_listing(sub, 'hot', limit=3)
    for p in listing.posts:
        result.append({'subreddit': sub, 'title': p.title, 'score': p.score})
"
```

### Example: enrich posts with author info
```bash
reddit exec -c "
listing = client.get_listing('python', 'top', limit=5, time='week')
for p in listing.posts:
    user = client.get_user_info(p.author)
    result.append({'title': p.title, 'author': p.author, 'karma': user.total_karma})
"
```

Output follows the standard envelope: `{"ok": true, "schema_version": "1", "data": [...]}`. On error: `{"ok": false, "error": {"code": "script_error", "message": "...", "detail": "Traceback..."}}`.

## Utility
```bash
reddit open <id_or_index>   # Open post in browser
```

## Pagination
Listing responses include an `after` cursor. Pass it to get the next page:
```bash
reddit sub hot python --limit 25 --after t3_abc123
```

## Worked Examples

**Task**: "What's trending in Python?"
```bash
reddit sub hot python --limit 5
```

**Task**: "Find discussions about async frameworks"
```bash
reddit search "async framework" --subreddit python --sort top --time year --limit 5
```

**Task**: "Get the full discussion on a post"
```bash
reddit post read <post_id> --limit 100 --depth 10 --expand
```

**Task**: "Export top Python posts to CSV"
```bash
reddit export "python" --subreddit python --count 50 --format csv --output results.csv
```

**Task**: "Upvote the 3rd post from last listing"
```bash
reddit vote 3
```

**Task**: "Browse, read, and interact with a post" (multi-step)
```bash
reddit sub hot python --limit 5          # list posts (populates index cache)
reddit post show 2 --expand              # read post #2 with full comments
reddit vote 2                            # upvote it
reddit save 2                            # save it
reddit comment 2 "Great discussion!"     # comment on it
```

## Rate Limits
Automatically throttled with Gaussian jitter (~1 req/sec for reads, ~2.5s for writes). Retries on 429 with exponential backoff.
