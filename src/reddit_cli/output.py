"""Output formatting: JSON, YAML, Rich table, compact mode."""

import json
import os
import sys
import time as _time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from reddit_cli.models import Comment, Listing, PostDetail

SCHEMA_VERSION = "1"

COMPACT_POST_FIELDS = {
    "id", "title", "subreddit", "author", "score",
    "num_comments", "permalink", "url", "created_utc", "is_self",
}


def resolve_output_format(*, as_json: bool, as_yaml: bool) -> str | None:
    """Resolve output format. Returns 'json', 'yaml', or None (for rich/auto)."""
    if as_json:
        return "json"
    if as_yaml:
        return "yaml"
    env = os.environ.get("OUTPUT", "").lower()
    if env in ("json", "yaml", "rich"):
        return env if env != "rich" else None
    return None


def _build_success_envelope(data: Any) -> dict:
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "data": data,
    }


def _build_error_envelope(code: str, message: str, detail: str | None = None) -> dict:
    error: dict[str, Any] = {"code": code, "message": message}
    if detail:
        error["detail"] = detail
    return {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "error": error,
    }


def _compact_data(data: dict) -> dict:
    """Strip non-essential fields for token-efficient output."""
    if "posts" in data:
        data = dict(data)
        data["posts"] = [
            {k: v for k, v in post.items() if k in COMPACT_POST_FIELDS}
            for post in data["posts"]
        ]
    return data


def output_json(data: BaseModel, success: bool = True, compact: bool = False) -> None:
    """Write JSON envelope to stdout."""
    dumped = data.model_dump(mode="json")
    if compact:
        dumped = _compact_data(dumped)
    envelope = _build_success_envelope(dumped)
    sys.stdout.write(json.dumps(envelope, indent=2, default=str))
    sys.stdout.write("\n")


def output_yaml(data: BaseModel, success: bool = True, compact: bool = False) -> None:
    """Write YAML envelope to stdout."""
    import yaml

    dumped = data.model_dump(mode="json")
    if compact:
        dumped = _compact_data(dumped)
    envelope = _build_success_envelope(dumped)
    sys.stdout.write(yaml.dump(envelope, default_flow_style=False, sort_keys=False))


def output_error(code: str | int, message: str, detail: str | None = None) -> None:
    """Write error envelope to stdout, human message to stderr."""
    envelope = _build_error_envelope(str(code), message, detail)
    sys.stdout.write(json.dumps(envelope, indent=2))
    sys.stdout.write("\n")
    sys.stderr.write(f"Error: {message}\n")


def output_table_posts(listing: Listing) -> None:
    """Render a listing as a Rich table to stdout."""
    console = Console()
    table = Table()
    table.add_column("Score", justify="right", style="green", width=7)
    table.add_column("Comments", justify="right", width=8)
    table.add_column("Title", style="bold", max_width=60)
    table.add_column("Author", style="dim")
    table.add_column("ID", style="dim")

    for post in listing.posts:
        table.add_row(
            format_score(post.score),
            str(post.num_comments),
            post.title[:60],
            post.author,
            post.id,
        )
    console.print(table)


def render_listing(listing: Listing, *, _console: Console | None = None) -> None:
    """Render a listing as a Rich table with emoji indicators and hints."""
    console = _console or Console(stderr=True)

    if not listing.posts:
        console.print("[yellow]No posts found[/yellow]")
        return

    table = Table(show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Score", style="yellow", width=6, justify="right")
    table.add_column("Subreddit", style="magenta", max_width=15)
    table.add_column("Title", style="bold cyan", max_width=60)
    table.add_column("Author", style="green", max_width=14)
    table.add_column("\U0001f4ac", style="dim", width=5, justify="right")
    table.add_column("Time", style="dim", max_width=10)

    for i, post in enumerate(listing.posts, 1):
        title_text = post.title or "-"
        if post.stickied:
            title_text = f"\U0001f4cc {title_text}"
        if post.over_18:
            title_text = f"\U0001f51e {title_text}"
        if post.is_video:
            title_text = f"\U0001f3ac {title_text}"

        table.add_row(
            str(i),
            format_score(post.score),
            f"r/{post.subreddit or '?'}",
            title_text[:60],
            (post.author or "-")[:14],
            str(post.num_comments),
            format_time(post.created_utc),
        )

    console.print(table)
    console.print("\n  [dim]Use [bold]reddit post show <#>[/bold] to read a post[/dim]")
    if listing.after:
        console.print(f"  [dim]More: use [bold]--after {listing.after}[/bold][/dim]")


def render_post_detail(detail: PostDetail, *, _console: Console | None = None) -> None:
    """Render post detail with comment tree."""
    from rich.panel import Panel

    console = _console or Console(stderr=True)
    post = detail.post

    # Post panel
    meta = (
        f"r/{post.subreddit} | u/{post.author}"
        f" | {format_score(post.score)} pts | {post.num_comments} comments"
    )
    body = post.selftext[:500] if post.selftext else post.url
    panel = Panel(
        f"{body}\n\n[dim]{meta}[/dim]",
        title=f"[bold]{post.title}[/bold]",
    )
    console.print(panel)

    # Comments
    comments = [c for c in detail.comments if isinstance(c, Comment)]
    if not comments:
        console.print("[dim]No comments[/dim]")
        return

    def _render_tree(items: list[Comment], depth: int = 0) -> None:
        for c in items:
            indent = "  " * depth
            author = c.author or "[deleted]"
            op_tag = " [bold yellow][OP][/bold yellow]" if c.is_submitter else ""
            score_style = "green" if c.score > 0 else ("red" if c.score < 0 else "dim")

            console.print(
                f"{indent}[green]u/{author}[/green]{op_tag}"
                f" [{score_style}]{c.score} pts[/{score_style}]"
            )
            for line in (c.body or "").split("\n"):
                console.print(f"{indent}  {line}")
            console.print()

            if c.replies:
                _render_tree(c.replies, depth + 1)

    _render_tree(comments)


def format_score(score: int) -> str:
    """Format score: 1500 -> '1.5k'."""
    if abs(score) >= 1000:
        return f"{score / 1000:.1f}k"
    return str(score)


def format_time(utc_timestamp: float) -> str:
    """Format timestamp as relative or absolute time."""
    now = _time.time()
    diff = now - utc_timestamp

    if diff < 60:
        return f"{int(diff)}s ago"
    if diff < 3600:
        return f"{int(diff // 60)}m ago"
    if diff < 86400:
        return f"{int(diff // 3600)}h ago"
    if diff < 86400 * 30:
        return f"{int(diff // 86400)}d ago"

    dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


# ── OutputContext + TTY-aware routing ──────────────────────────────────


@dataclass
class OutputContext:
    """Resolved output preferences for a command invocation."""

    format: str | None = None  # "json", "yaml", or None (auto/rich)
    compact: bool = False
    full_text: bool = False

    @classmethod
    def from_flags(
        cls,
        *,
        as_json: bool = False,
        as_yaml: bool = False,
        compact: bool = False,
        full_text: bool = False,
    ) -> "OutputContext":
        fmt = resolve_output_format(as_json=as_json, as_yaml=as_yaml)
        return cls(format=fmt, compact=compact, full_text=full_text)


def emit(
    data: BaseModel,
    ctx: OutputContext,
    *,
    render: Callable | None = None,
) -> None:
    """Route output: JSON, YAML, or Rich render based on context and TTY."""
    if ctx.format == "json":
        output_json(data, compact=ctx.compact)
    elif ctx.format == "yaml":
        output_yaml(data, compact=ctx.compact)
    elif sys.stdout.isatty() and render:
        render(data)
    else:
        output_json(data, compact=ctx.compact)  # Default: JSON (agent-friendly)


def exit_for_error(exc: Exception, ctx: OutputContext) -> None:
    """Emit error and terminate. Structured for machine, Rich for human."""
    from reddit_cli.errors import error_code_for_exception

    code = error_code_for_exception(exc)
    message = getattr(exc, "message", str(exc))
    detail = getattr(exc, "detail", None)
    exit_code = getattr(exc, "exit_code", 1)
    # Coerce IntEnum to int for SystemExit
    exit_code = int(exit_code)

    if ctx.format in ("json", "yaml") or not sys.stdout.isatty():
        output_error(code, message, detail)
    else:
        Console(stderr=True).print(f"[red][{code}] {message}[/red]")

    raise SystemExit(exit_code)
