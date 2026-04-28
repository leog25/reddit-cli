import typer
from pydantic import BaseModel

app = typer.Typer(help="User commands")


class RawResult(BaseModel):
    raw: dict


@app.command()
def info(
    username: str = typer.Argument(..., help="Reddit username"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
):
    """Get user profile information."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().get_user_info(username)

    handle_command(action=action, ctx=ctx)


@app.command()
def posts(
    username: str = typer.Argument(..., help="Reddit username"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse a user's submitted posts."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext, render_listing

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml, compact=compact)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().get_user_posts(username, limit=limit, after=after)

    handle_command(action=action, ctx=ctx, render=render_listing, save_listing=True)


@app.command()
def comments(
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
