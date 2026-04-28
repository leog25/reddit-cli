"""Tests for RuntimeConfig."""

import pytest


class TestRuntimeConfig:
    def test_default_values(self):
        from reddit_cli.config import RuntimeConfig

        config = RuntimeConfig()
        assert config.timeout == 30.0
        assert config.read_request_delay == 0.5
        assert config.write_request_delay == 2.5
        assert config.max_retries == 3
        assert config.status_check_timeout == 10.0

    def test_custom_values(self):
        from reddit_cli.config import RuntimeConfig

        config = RuntimeConfig(timeout=5.0, max_retries=1)
        assert config.timeout == 5.0
        assert config.max_retries == 1
        # Others keep defaults
        assert config.read_request_delay == 0.5

    def test_frozen(self):
        from reddit_cli.config import RuntimeConfig

        config = RuntimeConfig()
        with pytest.raises((TypeError, ValueError, AttributeError)):
            config.timeout = 99.0  # type: ignore

    def test_invalid_type_rejected(self):
        from reddit_cli.config import RuntimeConfig

        with pytest.raises((TypeError, ValueError)):
            RuntimeConfig(timeout="not a number")  # type: ignore

    def test_default_config_instance(self):
        from reddit_cli.config import DEFAULT_CONFIG, RuntimeConfig

        assert isinstance(DEFAULT_CONFIG, RuntimeConfig)
        assert DEFAULT_CONFIG.timeout == 30.0
