import typer

app = typer.Typer(help="Post commands")


@app.command()
def read(
    post_id: str = typer.Argument(..., help="Post ID, fullname (t3_xxx), or URL"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of top-level comments"),
    depth: int = typer.Option(3, "--depth", "-d", help="Comment nesting depth"),
    expand: bool = typer.Option(False, "--expand", "-e", help="Expand 'load more' comment stubs"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
):
    """Read a post and its comments."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext, render_post_detail

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().get_post(post_id, limit=limit, depth=depth, expand=expand)

    handle_command(action=action, ctx=ctx, render=render_post_detail)


@app.command()
def show(
    index: int = typer.Argument(..., help="Index number from last listing (1-based)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of top-level comments"),
    depth: int = typer.Option(3, "--depth", "-d", help="Comment nesting depth"),
    expand: bool = typer.Option(False, "--expand", "-e", help="Expand 'load more' comment stubs"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
):
    """Read a post by its index from the last listing."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.index_cache import get_item_by_index
    from reddit_cli.output import OutputContext, output_error, render_post_detail

    item = get_item_by_index(index)
    if not item:
        output_error("not_found", f"No item at index {index}. Run a listing command first.")
        raise SystemExit(3)

    post_id = item.get("id", "")
    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().get_post(post_id, limit=limit, depth=depth, expand=expand)

    handle_command(action=action, ctx=ctx, render=render_post_detail)
