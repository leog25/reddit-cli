"""Tests for auth TTL refresh warning."""

import time
from unittest.mock import patch

from reddit_cli.auth import Credential


class TestAuthRefresh:
    @patch("reddit_cli.auth.extract_browser_credential", return_value=None)
    @patch("reddit_cli.auth.CREDENTIAL_FILE")
    def test_stale_credential_warns_on_stderr(self, mock_file, mock_extract, capsys):
        """When credential refresh fails, a warning should appear on stderr."""
        # Create a stale credential (saved 8 days ago)
        stale_cred = Credential(
            cookies={"reddit_session": "abc"},
            source="browser:chrome",
            saved_at=time.time() - (8 * 86400),
        )
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = stale_cred.model_dump_json()

        from reddit_cli.auth import load_credential
        result = load_credential()

        # Should still return the stale credential
        assert result is not None
        assert result.cookies.get("reddit_session") == "abc"

        # Should warn on stderr
        captured = capsys.readouterr()
        err = captured.err.lower()
        assert "stale" in err or "warning" in err or "refresh" in err
