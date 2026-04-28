"""Write commands: vote, save, subscribe, comment."""

import typer
from pydantic import BaseModel


class VoteResult(BaseModel):
    message: str
    fullname: str
    direction: int


class SaveResult(BaseModel):
    message: str
    fullname: str


class SubscribeResult(BaseModel):
    message: str
    subreddit: str


class CommentResult(BaseModel):
    message: str
    parent: str


def vote(
    id_or_index: str = typer.Argument(
        ..., help="Post/comment ID, fullname, or index from last listing",
    ),
    down: bool = typer.Option(False, "--down", help="Downvote instead of upvote"),
    undo: bool = typer.Option(False, "--undo", help="Remove vote"),
):
    """Vote on a post or comment."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.index_cache import resolve_fullname_from_index
    from reddit_cli.output import OutputContext

    fullname = resolve_fullname_from_index(id_or_index)
    direction = 0 if undo else (-1 if down else 1)
    ctx = OutputContext.from_flags(as_json=True)

    def action():
        from reddit_cli.client import RedditClient
        RedditClient().vote(fullname, direction=direction)
        return VoteResult(message="Vote recorded", fullname=fullname, direction=direction)

    handle_command(action=action, ctx=ctx)


def save(
    id_or_index: str = typer.Argument(..., help="Post ID, fullname, or index"),
    undo: bool = typer.Option(False, "--undo", help="Unsave instead"),
):
    """Save or unsave a post."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.index_cache import resolve_fullname_from_index
    from reddit_cli.output import OutputContext

    fullname = resolve_fullname_from_index(id_or_index)
    ctx = OutputContext.from_flags(as_json=True)

    def action():
        from reddit_cli.client import RedditClient
        client = RedditClient()
        if undo:
            client.unsave_item(fullname)
        else:
            client.save_item(fullname)
        label = "Unsaved" if undo else "Saved"
        return SaveResult(message=label, fullname=fullname)

    handle_command(action=action, ctx=ctx)


def subscribe_cmd(
    subreddit: str = typer.Argument(..., help="Subreddit name"),
    undo: bool = typer.Option(False, "--undo", help="Unsubscribe instead"),
):
    """Subscribe or unsubscribe to a subreddit."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext

    api_action = "unsub" if undo else "sub"
    ctx = OutputContext.from_flags(as_json=True)

    def action():
        from reddit_cli.client import RedditClient
        RedditClient().subscribe(subreddit, action=api_action)
        msg = "Unsubscribed" if undo else "Subscribed"
        return SubscribeResult(message=msg, subreddit=subreddit)

    handle_command(action=action, ctx=ctx)


def comment(
    id_or_index: str = typer.Argument(..., help="Post/comment ID, fullname, or index"),
    text: str = typer.Argument(..., help="Comment text"),
):
    """Post a comment on a post or reply to a comment."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.index_cache import resolve_fullname_from_index
    from reddit_cli.output import OutputContext

    fullname = resolve_fullname_from_index(id_or_index)
    ctx = OutputContext.from_flags(as_json=True)

    def action():
        from reddit_cli.client import RedditClient
        RedditClient().post_comment(fullname, text)
        return CommentResult(message="Comment posted", parent=fullname)

    handle_command(action=action, ctx=ctx)
