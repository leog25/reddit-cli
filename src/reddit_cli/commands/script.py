"""Execute Python scripts with a pre-initialized RedditClient."""

import io
import json
import sys
import threading
import traceback
from pathlib import Path
from time import sleep

import typer
from pydantic import BaseModel

from reddit_cli.output import _build_success_envelope, output_error


def exec_script(
    file: str = typer.Argument(None, help="Python script file (use '-' for stdin)"),
    code: str | None = typer.Option(None, "-c", "--code", help="Inline Python code"),
    timeout: int = typer.Option(120, "--timeout", "-t", help="Timeout in seconds"),
):
    """Run a Python script with a pre-initialized RedditClient.

    The script has access to: client, result, Post, Comment, Listing,
    PostDetail, SubredditInfo, UserInfo, sleep.

    Append items to the ``result`` list; they are emitted as JSON on exit.
    """
    # ── resolve source ───────────────────────────────────────────────
    if code is not None and file is not None:
        output_error("usage", "Provide either a file or -c, not both")
        raise SystemExit(2)

    if code is not None:
        source = code
        filename = "<string>"
    elif file == "-":
        source = sys.stdin.read()
        filename = "<stdin>"
    elif file is not None:
        path = Path(file)
        if not path.exists():
            output_error("file_not_found", f"File not found: {file}")
            raise SystemExit(1)
        source = path.read_text(encoding="utf-8")
        filename = file
    else:
        output_error("usage", "Provide a script file or -c '<code>'")
        raise SystemExit(2)

    # ── compile ──────────────────────────────────────────────────────
    try:
        compiled = compile(source, filename, "exec")
    except SyntaxError as exc:
        output_error("script_error", str(exc), detail=traceback.format_exc())
        raise SystemExit(1) from None

    # ── execute with client ──────────────────────────────────────────
    from reddit_cli.client import RedditClient
    from reddit_cli.models import (
        Comment,
        Listing,
        Post,
        PostDetail,
        SubredditInfo,
        UserInfo,
    )

    with RedditClient() as client:
        result: list = []
        namespace = {
            "client": client,
            "result": result,
            "Post": Post,
            "Comment": Comment,
            "Listing": Listing,
            "PostDetail": PostDetail,
            "SubredditInfo": SubredditInfo,
            "UserInfo": UserInfo,
            "sleep": sleep,
        }

        script_exc: BaseException | None = None
        script_stdout = io.StringIO()
        namespace["print"] = lambda *a, **kw: print(
            *a, **{**kw, "file": kw.get("file", script_stdout)},
        )

        def _run():
            nonlocal script_exc
            try:
                exec(compiled, namespace)  # noqa: S102
            except SystemExit as exc:
                if exc.code not in (None, 0):
                    script_exc = exc
            except BaseException as exc:
                script_exc = exc

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            output_error("timeout", f"Script exceeded {timeout}s timeout")
            raise SystemExit(1)

        if script_exc is not None:
            tb = "".join(traceback.format_exception(script_exc))
            output_error("script_error", str(script_exc), detail=tb)
            raise SystemExit(1)

        # ── serialize result ─────────────────────────────────────────
        serialized = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            for item in result
        ]
        envelope = _build_success_envelope(serialized)
        sys.stdout.write(json.dumps(envelope, indent=2, default=str))
        sys.stdout.write("\n")
