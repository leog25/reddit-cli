"""Shared command helpers: handle_command, auth gates."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from reddit_cli.errors import RedditAPIError
from reddit_cli.index_cache import save_index
from reddit_cli.models import Listing
from reddit_cli.output import OutputContext, emit, exit_for_error


def handle_command(
    *,
    action: Callable[[], BaseModel],
    ctx: OutputContext,
    render: Callable | None = None,
    save_listing: bool = False,
) -> BaseModel | None:
    """Run an action, emit output, handle errors.

    - action: zero-arg callable returning a Pydantic model
    - ctx: output context (json/yaml/rich)
    - render: optional Rich render function for TTY mode
    - save_listing: if True and result is a Listing, save to index cache
    """
    try:
        data = action()
        if save_listing and isinstance(data, Listing):
            save_index([p.model_dump(mode="json") for p in data.posts])
        emit(data, ctx, render=render)
        return data
    except RedditAPIError as exc:
        exit_for_error(exc, ctx)
        return None  # unreachable


def require_auth():
    """Load credential or exit with auth error. For write commands."""
    from reddit_cli.auth import load_credential
    from reddit_cli.output import output_error

    cred = load_credential()
    if not cred or not cred.is_valid:
        output_error("not_authenticated", "Not logged in. Use 'reddit auth login' to authenticate.")
        raise SystemExit(1)
    return cred


def optional_auth():
    """Load credential if available, return None otherwise. For read commands."""
    from reddit_cli.auth import load_credential

    return load_credential()
