
import typer


def search(
    query: str = typer.Argument(..., help="Search query"),
    subreddit: str | None = typer.Option(
        None, "--subreddit", "-s", help="Restrict to subreddit",
    ),
    sort: str = typer.Option(
        "relevance", "--sort", help="Sort: relevance, hot, top, new, comments",
    ),
    time: str = typer.Option(
        "all", "--time", "-t", help="Time: all, hour, day, week, month, year",
    ),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of results (1-100)"),
    after: str | None = typer.Option(None, "--after", "-a", help="Pagination cursor"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Search Reddit posts."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext, render_listing

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml, compact=compact)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().search(
            query, subreddit=subreddit, sort=sort,
            time=time, limit=limit, after=after,
        )

    handle_command(action=action, ctx=ctx, render=render_listing, save_listing=True)
