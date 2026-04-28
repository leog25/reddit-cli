import subprocess
import sys


class TestStartup:
    def test_help_works_without_error(self):
        """Verify --help completes successfully (validates lazy imports don't break)."""
        result = subprocess.run(
            [sys.executable, "-c", "from reddit_cli.main import cli; cli()"],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            env={**__import__("os").environ, "COLUMNS": "120"},
        )
        # Typer with no_args_is_help shows help (exit 0 or 2 depending on version)
        assert result.returncode in (0, 2)
        combined = result.stdout + result.stderr
        assert "sub" in combined.lower() or "search" in combined.lower()

    def test_help_does_not_import_httpx(self):
        """Verify importing the app doesn't trigger httpx import."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; from reddit_cli.main import app; "
                "assert 'httpx' not in sys.modules, "
                "'httpx was imported at app load time'",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"httpx imported too early: {result.stderr}"
