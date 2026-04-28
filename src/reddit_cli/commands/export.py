"""Export command: search and save results to CSV or JSON file."""

import csv
import json

import typer
from pydantic import BaseModel


class ExportResult(BaseModel):
    message: str
    count: int
    file: str
    format: str


def export(
    query: str = typer.Argument(..., help="Search query"),
    subreddit: str | None = typer.Option(None, "--subreddit", "-s", help="Restrict to subreddit"),
    count: int = typer.Option(25, "--count", "-n", help="Number of results to export"),
    output: str = typer.Option("export.json", "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json or csv"),
):
    """Export search results to a JSON or CSV file."""
    from reddit_cli.commands.helpers import handle_command
    from reddit_cli.output import OutputContext

    ctx = OutputContext.from_flags(as_json=True)

    def action():
        from reddit_cli.client import RedditClient
        client = RedditClient()
        all_posts = []
        after = None
        remaining = count

        while remaining > 0:
            batch_size = min(remaining, 100)
            listing = client.search(query, subreddit=subreddit, limit=batch_size, after=after)
            if not listing.posts:
                break
            all_posts.extend(listing.posts)
            remaining -= len(listing.posts)
            after = listing.after
            if not after:
                break

        rows = [p.model_dump(mode="json") for p in all_posts[:count]]

        if format == "csv":
            if rows:
                fields = [
                    "id", "title", "subreddit", "author", "score",
                    "num_comments", "permalink", "url", "created_utc",
                ]
                with open(output, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(rows)
            else:
                with open(output, "w", encoding="utf-8") as f:
                    f.write("")
        else:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, default=str)

        return ExportResult(
            message=f"Exported {len(rows)} posts",
            count=len(rows),
            file=output,
            format=format,
        )

    handle_command(action=action, ctx=ctx)
