"""Auth commands: login, logout, status, whoami."""

import typer

app = typer.Typer(help="Authentication commands")


@app.command()
def login():
    """Extract Reddit cookies from your browser and save them."""
    from reddit_cli.auth import extract_browser_credential, load_credential
    from reddit_cli.output import output_error, output_json

    existing = load_credential()
    if existing and existing.is_valid:
        from pydantic import BaseModel

        class LoginResult(BaseModel):
            message: str
            source: str
            cookie_count: int

        output_json(LoginResult(
            message="Already logged in",
            source=existing.source,
            cookie_count=len(existing.cookies),
        ))
        return

    cred = extract_browser_credential()
    if cred:
        from pydantic import BaseModel

        class LoginResult(BaseModel):
            message: str
            source: str
            cookie_count: int

        output_json(LoginResult(
            message="Login successful",
            source=cred.source,
            cookie_count=len(cred.cookies),
        ))
    else:
        output_error(
            "not_authenticated",
            "No Reddit cookies found in any browser."
            " Try 'reddit auth set-cookie <value>' instead.",
        )
        raise SystemExit(1)


@app.command()
def set_cookie(
    cookie_value: str = typer.Argument(
        ..., help="reddit_session cookie value from browser DevTools",
    ),
):
    """Manually set the reddit_session cookie.

    Get it from browser DevTools: Application > Cookies > reddit.com > reddit_session.
    """
    from pydantic import BaseModel

    from reddit_cli.auth import Credential, save_credential
    from reddit_cli.output import output_json

    cred = Credential(
        cookies={"reddit_session": cookie_value},
        source="manual",
    )
    save_credential(cred)

    class SetCookieResult(BaseModel):
        message: str
        source: str

    output_json(SetCookieResult(message="Cookie saved", source="manual"))


@app.command()
def logout():
    """Clear saved Reddit credentials."""
    from pydantic import BaseModel

    from reddit_cli.auth import clear_credential
    from reddit_cli.output import output_json

    class LogoutResult(BaseModel):
        message: str

    clear_credential()
    output_json(LogoutResult(message="Logged out"))


@app.command()
def status(
    validate: bool = typer.Option(False, "--validate", "-v", help="Validate session with Reddit"),
    as_json: bool = typer.Option(False, "--json", help="Force JSON output"),
    as_yaml: bool = typer.Option(False, "--yaml", help="Force YAML output"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
):
    """Check authentication status."""
    from pydantic import BaseModel

    from reddit_cli.auth import load_credential
    from reddit_cli.output import OutputContext, emit, output_error
    from reddit_cli.session import SessionState

    cred = load_credential()
    if not cred:
        output_error("not_authenticated", "Not logged in")
        raise SystemExit(1)

    session = SessionState(
        cookies=dict(cred.cookies),
        source=cred.source,
        username=cred.username,
        modhash=cred.modhash,
    )
    session.refresh_capabilities()

    class StatusResult(BaseModel):
        authenticated: bool
        username: str | None = None
        source: str
        cookie_count: int
        can_write: bool
        modhash_present: bool

    ctx = OutputContext.from_flags(as_json=as_json, as_yaml=as_yaml, compact=compact)
    emit(StatusResult(
        authenticated=session.is_authenticated,
        username=session.username,
        source=session.source,
        cookie_count=len(session.cookies),
        can_write=session.can_write,
        modhash_present=bool(session.modhash),
    ), ctx)


@app.command()
def whoami():
    """Show the currently authenticated user's profile."""
    from reddit_cli.commands.helpers import handle_command, require_auth
    from reddit_cli.output import OutputContext

    require_auth()
    ctx = OutputContext.from_flags(as_json=True)

    def action():
        from reddit_cli.client import RedditClient
        return RedditClient().get_me()

    handle_command(action=action, ctx=ctx)
