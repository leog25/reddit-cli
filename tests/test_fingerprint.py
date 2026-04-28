"""Tests for BrowserFingerprint."""


class TestBrowserFingerprint:
    def test_chrome133_mac_creates_instance(self):
        from reddit_cli.fingerprint import BrowserFingerprint

        fp = BrowserFingerprint.chrome133_mac()
        assert "Chrome/133" in fp.user_agent
        assert "macOS" in fp.sec_ch_ua_platform

    def test_base_headers_keys(self):
        from reddit_cli.fingerprint import BrowserFingerprint

        fp = BrowserFingerprint.chrome133_mac()
        headers = fp.base_headers()
        assert "User-Agent" in headers
        assert "sec-ch-ua" in headers
        assert "sec-ch-ua-mobile" in headers
        assert "sec-ch-ua-platform" in headers
        assert "Accept" in headers

    def test_read_headers_same_as_base(self):
        from reddit_cli.fingerprint import BrowserFingerprint

        fp = BrowserFingerprint.chrome133_mac()
        assert fp.read_headers() == fp.base_headers()

    def test_write_headers_adds_origin(self):
        from reddit_cli.fingerprint import BrowserFingerprint

        fp = BrowserFingerprint.chrome133_mac()
        headers = fp.write_headers()
        assert "Origin" in headers
        assert "Referer" in headers
        assert "Content-Type" in headers

    def test_write_headers_with_modhash(self):
        from reddit_cli.fingerprint import BrowserFingerprint

        fp = BrowserFingerprint.chrome133_mac()
        headers = fp.write_headers(modhash="abc123")
        assert headers["x-modhash"] == "abc123"

    def test_write_headers_no_modhash(self):
        from reddit_cli.fingerprint import BrowserFingerprint

        fp = BrowserFingerprint.chrome133_mac()
        headers = fp.write_headers()
        assert "x-modhash" not in headers

    def test_frozen(self):
        import pytest

        from reddit_cli.fingerprint import BrowserFingerprint

        fp = BrowserFingerprint.chrome133_mac()
        with pytest.raises((TypeError, ValueError, AttributeError)):
            fp.user_agent = "changed"  # type: ignore
