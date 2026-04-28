"""Exception hierarchy and exit codes for Reddit CLI."""

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1
    USAGE = 2
    NOT_FOUND = 3
    RATE_LIMITED = 4


class RedditAPIError(Exception):
    """Base exception for Reddit API errors."""

    def __init__(self, exit_code: int = 1, message: str = "", detail: str | None = None):
        self.exit_code = exit_code
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(RedditAPIError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            exit_code=ExitCode.NOT_FOUND,
            message=f"{resource} not found",
        )


class RateLimitError(RedditAPIError):
    def __init__(self, retry_after: float | None = None):
        msg = "Rate limited by Reddit"
        if retry_after:
            msg += f" (retry after {retry_after:.0f}s)"
        super().__init__(
            exit_code=ExitCode.RATE_LIMITED,
            message=msg,
            detail="Too many requests",
        )
        self.retry_after = retry_after


class ForbiddenError(RedditAPIError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            exit_code=ExitCode.ERROR,
            message=f"Access forbidden: {resource}",
        )


class AuthRequiredError(RedditAPIError):
    def __init__(self):
        super().__init__(
            exit_code=ExitCode.ERROR,
            message="Not logged in. Use 'reddit auth login' to authenticate",
        )


class SessionExpiredError(RedditAPIError):
    def __init__(self):
        super().__init__(
            exit_code=ExitCode.ERROR,
            message="Session expired. Please re-login: reddit auth logout && reddit auth login",
        )


def error_code_for_exception(exc: Exception) -> str:
    """Map exceptions to stable string error codes for agent consumption."""
    if isinstance(exc, (AuthRequiredError, SessionExpiredError)):
        return "not_authenticated"
    if isinstance(exc, RateLimitError):
        return "rate_limited"
    if isinstance(exc, NotFoundError):
        return "not_found"
    if isinstance(exc, ForbiddenError):
        return "forbidden"
    if isinstance(exc, RedditAPIError):
        return "api_error"
    return "unknown_error"
