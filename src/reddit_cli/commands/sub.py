
import typer

app = typer.Typer(help="Subreddit commands")


def _listing_command(
    subreddit: str, sort: str, limit: int, time: str = "day", after: str | None = None,
    as_json: bool = False, as_yaml: bool = False, compact: bool = False,
):
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext, render_listing

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml, compact=compact)

    def action():
        from reddit_cli.client import RedditClient
        kwargs: dict = {"limit": limit, "after": after}
        if sort == "top":
            kwargs["time"] = time
        return RedditClient().get_listing(subreddit, sort, **kwargs)

    handle_command(action=action, ctx=ctx, render=render_listing, save_listing=True)


@app.command()
def hot(
    subreddit: str = typer.Argument(..., help="Subreddit name"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse hot posts in a subreddit."""
    _listing_command(
        subreddit, "hot", limit, after=after,
        as_json=as_json, as_yaml=as_yaml, compact=compact,
    )


@app.command()
def new(
    subreddit: str = typer.Argument(..., help="Subreddit name"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse new posts in a subreddit."""
    _listing_command(
        subreddit, "new", limit, after=after,
        as_json=as_json, as_yaml=as_yaml, compact=compact,
    )


@app.command()
def top(
    subreddit: str = typer.Argument(..., help="Subreddit name"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    time: str = typer.Option(
        "day", "--time", "-t", help="Time: hour, day, week, month, year, all",
    ),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse top posts in a subreddit."""
    _listing_command(
        subreddit, "top", limit, time=time, after=after,
        as_json=as_json, as_yaml=as_yaml, compact=compact,
    )


@app.command()
def rising(
    subreddit: str = typer.Argument(..., help="Subreddit name"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of posts (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Browse rising posts in a subreddit."""
    _listing_command(
        subreddit, "rising", limit, after=after,
        as_json=as_json, as_yaml=as_yaml, compact=compact,
    )


@app.command()
def info(
    subreddit: str = typer.Argument(..., help="Subreddit name"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
):
    """Get subreddit metadata."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().get_subreddit_info(subreddit)

    handle_command(action=action, ctx=ctx)
