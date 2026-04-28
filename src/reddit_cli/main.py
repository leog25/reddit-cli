import typer

from reddit_cli.commands import auth, browse, export, post, script, search, social, sub, user

app = typer.Typer(
    name="reddit",
    help="CLI for AI agents to interact with Reddit",
    no_args_is_help=True,
)

app.add_typer(auth.app, name="auth")
app.add_typer(sub.app, name="sub")
app.add_typer(post.app, name="post")
app.add_typer(user.app, name="user")
app.command(name="search")(search.search)
app.command(name="vote")(social.vote)
app.command(name="save")(social.save)
app.command(name="subscribe")(social.subscribe_cmd)
app.command(name="comment")(social.comment)
app.command(name="popular")(browse.popular)
app.command(name="all")(browse.all_posts)
app.command(name="feed")(browse.feed)
app.command(name="open")(browse.open_cmd)
app.command(name="saved")(browse.saved)
app.command(name="upvoted")(browse.upvoted)
app.command(name="export")(export.export)
app.command(name="exec")(script.exec_script)


def cli():
    app()


if __name__ == "__main__":
    cli()
