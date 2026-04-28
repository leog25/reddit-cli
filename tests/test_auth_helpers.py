"""Tests for require_auth() and optional_auth() helpers."""

from unittest.mock import patch

import pytest

from reddit_cli.auth import Credential


class TestRequireAuth:
    @patch("reddit_cli.auth.load_credential")
    def test_returns_credential_when_valid(self, mock_load):
        from reddit_cli.commands.helpers import require_auth
        cred = Credential(cookies={"reddit_session": "abc"})
        mock_load.return_value = cred
        result = require_auth()
        assert result is cred

    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_exits_when_no_credential(self, mock_load, capsys):
        from reddit_cli.commands.helpers import require_auth
        with pytest.raises(SystemExit) as exc_info:
            require_auth()
        assert exc_info.value.code == 1

    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_error_message_includes_login_hint(self, mock_load, capsys):
        from reddit_cli.commands.helpers import require_auth
        with pytest.raises(SystemExit):
            require_auth()
        captured = capsys.readouterr()
        assert "login" in captured.out.lower() or "login" in captured.err.lower()


class TestOptionalAuth:
    @patch("reddit_cli.auth.load_credential", return_value=None)
    def test_returns_none_when_no_credential(self, mock_load):
        from reddit_cli.commands.helpers import optional_auth
        assert optional_auth() is None

    @patch("reddit_cli.auth.load_credential")
    def test_returns_credential_when_available(self, mock_load):
        from reddit_cli.commands.helpers import optional_auth
        cred = Credential(cookies={"reddit_session": "abc"})
        mock_load.return_value = cred
        assert optional_auth() is cred
