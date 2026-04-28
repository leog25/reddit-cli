"""Browse expansion commands: feed, popular, all, user posts/comments, open."""

import platform
import subprocess

import typer
from pydantic import BaseModel


class RawResult(BaseModel):
    raw: dict


class OpenResult(BaseModel):
    message: str
    url: str


def _listing_cmd(
    method_name: str, *args, limit: int = 25, after: str | None = None,
    as_json: bool = False, as_yaml: bool = False, compact: bool = False,
):
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext, render_listing

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml, compact=compact)

    def action():
        from reddit_cli.client import RedditClient
        client = RedditClient()
        method = getattr(client, method_name)
        return method(*args, limit=limit, after=after)

    handle_command(action=action, ctx=ctx, render=render_listing, save_listing=True)


def popular(
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse popular posts across Reddit."""
    _listing_cmd(
        "get_popular", limit=limit, after=after,
        as_json=as_json, as_yaml=as_yaml, compact=compact,
    )


def all_posts(
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse r/all posts."""
    _listing_cmd(
        "get_all", limit=limit, after=after,
        as_json=as_json, as_yaml=as_yaml, compact=compact,
    )


def feed(
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse your home feed (may require auth for personalized results)."""
    _listing_cmd(
        "get_home", limit=limit, after=after,
        as_json=as_json, as_yaml=as_yaml, compact=compact,
    )


def user_posts(
    username: str = typer.Argument(..., help="Reddit username"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse a user's submitted posts."""
    _listing_cmd(
        "get_user_posts", username, limit=limit, after=after,
        as_json=as_json, as_yaml=as_yaml, compact=compact,
    )


def user_comments(
    username: str = typer.Argument(..., help="Reddit username"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of comments"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse a user's comments."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml, compact=compact)

    def action():
        from reddit_cli.client import RedditClient
        data = RedditClient().get_user_comments(username, limit=limit, after=after)
        return RawResult(raw=data)

    handle_command(action=action, ctx=ctx)


def saved(
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse your saved posts (requires auth)."""
    from reddit_cli.commands.helpers import handle_command, require_auth
    from reddit_cli.output import OutputContext, render_listing

    cred = require_auth()
    username = cred.username
    if not username:
        from reddit_cli.output import output_error
        output_error("not_authenticated", "Username not available. Run 'reddit auth login'.")
        raise SystemExit(1)

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml, compact=compact)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().get_saved(username, limit=limit, after=after)

    handle_command(action=action, ctx=ctx, render=render_listing, save_listing=True)


def upvoted(
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse your upvoted posts (requires auth)."""
    from reddit_cli.commands.helpers import handle_command, require_auth
    from reddit_cli.output import OutputContext, render_listing

    cred = require_auth()
    username = cred.username
    if not username:
        from reddit_cli.output import output_error
        output_error("not_authenticated", "Username not available. Run 'reddit auth login'.")
        raise SystemExit(1)

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml, compact=compact)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().get_upvoted(username, limit=limit, after=after)

    handle_command(action=action, ctx=ctx, render=render_listing, save_listing=True)


def open_url(url: str) -> None:
    """Open a URL in the default browser."""
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", url], check=False)
    elif system == "Windows":
        subprocess.run(["start", url], shell=True, check=False)
    else:
        subprocess.run(["xdg-open", url], check=False)


def open_cmd(
    id_or_index: str = typer.Argument(..., help="Post ID, URL, or index from last listing"),
):
    """Open a post in the default browser."""
    from reddit_cli.output import output_json

    # If it's a URL, open directly
    if id_or_index.startswith("http"):
        open_url(id_or_index)
        output_json(OpenResult(message="Opened in browser", url=id_or_index))
        return

    # Try index cache
    if id_or_index.isdigit():
        from reddit_cli.index_cache import get_item_by_index
        item = get_item_by_index(int(id_or_index))
        if item and item.get("permalink"):
            url = f"https://www.reddit.com{item['permalink']}"
            open_url(url)
            output_json(OpenResult(message="Opened in browser", url=url))
            return

    # Construct URL from ID
    url = f"https://www.reddit.com/comments/{id_or_index}"
    open_url(url)
    output_json(OpenResult(message="Opened in browser", url=url))
