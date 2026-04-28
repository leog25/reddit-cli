"""Tests for auth module: Credential, persistence, browser extraction."""

import time
from unittest.mock import patch


class TestCredential:
    def test_create_credential(self):
        from reddit_cli.auth import Credential

        cred = Credential(cookies={"reddit_session": "abc"}, source="browser:chrome")
        assert cred.cookies["reddit_session"] == "abc"
        assert cred.source == "browser:chrome"

    def test_round_trip_json(self):
        from reddit_cli.auth import Credential

        cred = Credential(
            cookies={"reddit_session": "abc", "csrf_token": "xyz"},
            source="test",
            username="testuser",
            modhash="mh123",
            saved_at=1700000000.0,
        )
        json_str = cred.model_dump_json()
        restored = Credential.model_validate_json(json_str)
        assert restored.cookies == cred.cookies
        assert restored.username == cred.username
        assert restored.modhash == cred.modhash

    def test_is_valid(self):
        from reddit_cli.auth import Credential

        valid = Credential(cookies={"reddit_session": "abc"})
        assert valid.is_valid

        empty = Credential(cookies={})
        assert not empty.is_valid


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        from reddit_cli.auth import Credential, load_credential, save_credential

        with patch("reddit_cli.auth.CREDENTIAL_FILE", tmp_path / "cred.json"), \
             patch("reddit_cli.auth.CONFIG_DIR", tmp_path):
            cred = Credential(cookies={"reddit_session": "abc"}, source="test")
            save_credential(cred)

            loaded = load_credential()
            assert loaded is not None
            assert loaded.cookies["reddit_session"] == "abc"

    def test_load_missing_returns_none(self, tmp_path):
        from reddit_cli.auth import load_credential

        with patch("reddit_cli.auth.CREDENTIAL_FILE", tmp_path / "nonexistent.json"):
            assert load_credential() is None

    def test_clear_credential(self, tmp_path):
        from reddit_cli.auth import clear_credential

        cred_file = tmp_path / "cred.json"
        cred_file.write_text("{}")
        with patch("reddit_cli.auth.CREDENTIAL_FILE", cred_file):
            clear_credential()
            assert not cred_file.exists()

    def test_ttl_refresh_triggers(self, tmp_path):
        from reddit_cli.auth import Credential, load_credential, save_credential

        with patch("reddit_cli.auth.CREDENTIAL_FILE", tmp_path / "cred.json"), \
             patch("reddit_cli.auth.CONFIG_DIR", tmp_path), \
             patch("reddit_cli.auth.extract_browser_credential") as mock_extract:
            # Save old credential
            old = Credential(
                cookies={"reddit_session": "old"},
                source="test",
                saved_at=time.time() - (8 * 86400),  # 8 days ago
            )
            save_credential(old)

            # Mock fresh extraction
            fresh = Credential(cookies={"reddit_session": "new"}, source="browser:chrome")
            mock_extract.return_value = fresh

            loaded = load_credential()
            assert loaded is not None
            assert loaded.cookies["reddit_session"] == "new"
            mock_extract.assert_called_once()


class TestBrowserExtraction:
    def test_get_credential_returns_saved(self, tmp_path):
        from reddit_cli.auth import Credential, get_credential, save_credential

        with patch("reddit_cli.auth.CREDENTIAL_FILE", tmp_path / "cred.json"), \
             patch("reddit_cli.auth.CONFIG_DIR", tmp_path):
            cred = Credential(cookies={"reddit_session": "saved"}, source="test")
            save_credential(cred)

            result = get_credential()
            assert result is not None
            assert result.cookies["reddit_session"] == "saved"

    def test_get_credential_returns_none_when_nothing(self, tmp_path):
        from reddit_cli.auth import get_credential

        with patch("reddit_cli.auth.CREDENTIAL_FILE", tmp_path / "nonexistent.json"), \
             patch("reddit_cli.auth.extract_browser_credential", return_value=None):
            assert get_credential() is None


class TestSessionState:
    def test_unauthenticated(self):
        from reddit_cli.session import SessionState

        session = SessionState()
        session.refresh_capabilities()
        assert not session.is_authenticated
        assert not session.can_write

    def test_read_capability(self):
        from reddit_cli.session import SessionState

        session = SessionState(cookies={"reddit_session": "abc"})
        session.refresh_capabilities()
        assert session.is_authenticated
        assert not session.can_write

    def test_write_capability(self):
        from reddit_cli.session import SessionState

        session = SessionState(cookies={"reddit_session": "abc"}, modhash="mh123")
        session.refresh_capabilities()
        assert session.is_authenticated
        assert session.can_write

    def test_apply_identity(self):
        from reddit_cli.session import SessionState

        session = SessionState(cookies={"reddit_session": "abc"})
        session.refresh_capabilities()
        assert not session.can_write

        session.apply_identity({"data": {"name": "testuser", "modhash": "mh456"}})
        assert session.username == "testuser"
        assert session.modhash == "mh456"
        assert session.can_write
