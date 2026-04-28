"""Tests for the exception hierarchy and string error codes."""


class TestExceptionHierarchy:
    def test_all_subclass_reddit_api_error(self):
        from reddit_cli.errors import (
            AuthRequiredError,
            ForbiddenError,
            NotFoundError,
            RateLimitError,
            RedditAPIError,
            SessionExpiredError,
        )

        assert issubclass(AuthRequiredError, RedditAPIError)
        assert issubclass(SessionExpiredError, RedditAPIError)
        assert issubclass(RateLimitError, RedditAPIError)
        assert issubclass(NotFoundError, RedditAPIError)
        assert issubclass(ForbiddenError, RedditAPIError)

    def test_not_found_error(self):
        from reddit_cli.errors import NotFoundError

        err = NotFoundError("Subreddit")
        assert "not found" in str(err).lower()
        assert err.exit_code == 3

    def test_rate_limit_error(self):
        from reddit_cli.errors import RateLimitError

        err = RateLimitError(retry_after=60.0)
        assert err.retry_after == 60.0
        assert err.exit_code == 4

    def test_forbidden_error(self):
        from reddit_cli.errors import ForbiddenError

        err = ForbiddenError("private subreddit")
        assert err.exit_code == 1

    def test_auth_required_error(self):
        from reddit_cli.errors import AuthRequiredError

        err = AuthRequiredError()
        assert err.exit_code == 1

    def test_session_expired_error(self):
        from reddit_cli.errors import SessionExpiredError

        err = SessionExpiredError()
        assert err.exit_code == 1


class TestErrorCodes:
    def test_not_found_code(self):
        from reddit_cli.errors import NotFoundError, error_code_for_exception

        assert error_code_for_exception(NotFoundError()) == "not_found"

    def test_rate_limited_code(self):
        from reddit_cli.errors import RateLimitError, error_code_for_exception

        assert error_code_for_exception(RateLimitError()) == "rate_limited"

    def test_forbidden_code(self):
        from reddit_cli.errors import ForbiddenError, error_code_for_exception

        assert error_code_for_exception(ForbiddenError()) == "forbidden"

    def test_auth_required_code(self):
        from reddit_cli.errors import AuthRequiredError, error_code_for_exception

        assert error_code_for_exception(AuthRequiredError()) == "not_authenticated"

    def test_session_expired_code(self):
        from reddit_cli.errors import SessionExpiredError, error_code_for_exception

        assert error_code_for_exception(SessionExpiredError()) == "not_authenticated"

    def test_base_error_code(self):
        from reddit_cli.errors import RedditAPIError, error_code_for_exception

        assert error_code_for_exception(RedditAPIError(1, "oops")) == "api_error"

    def test_unknown_error_code(self):
        from reddit_cli.errors import error_code_for_exception

        assert error_code_for_exception(ValueError("x")) == "unknown_error"


class TestBackwardCompat:
    def test_exit_code_enum_still_works(self):
        from reddit_cli.errors import ExitCode

        assert ExitCode.SUCCESS == 0
        assert ExitCode.NOT_FOUND == 3
        assert ExitCode.RATE_LIMITED == 4

    def test_old_reddit_api_error_still_works(self):
        from reddit_cli.errors import RedditAPIError

        err = RedditAPIError(3, "Not found", detail="gone")
        assert err.exit_code == 3
        assert err.message == "Not found"
        assert err.detail == "gone"
