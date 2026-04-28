"""Session capability detection and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _cookie_value(cookies: dict[str, str], *names: str) -> str | None:
    for name in names:
        value = cookies.get(name)
        if value:
            return value
    return None


@dataclass
class SessionState:
    """Normalized session information derived from saved/browser cookies."""

    cookies: dict[str, str] = field(default_factory=dict)
    source: str = "unknown"
    username: str | None = None
    modhash: str | None = None
    last_verified_at: float | None = None
    validation_error: str | None = None
    capabilities: set[str] = field(default_factory=set)

    @property
    def is_authenticated(self) -> bool:
        return "read" in self.capabilities

    @property
    def can_write(self) -> bool:
        return "write" in self.capabilities

    def refresh_capabilities(self) -> None:
        capabilities: set[str] = set()
        if self.cookies.get("reddit_session"):
            capabilities.add("read")

        inferred_modhash = self.modhash or _cookie_value(self.cookies, "modhash", "csrf_token")
        if inferred_modhash:
            self.modhash = inferred_modhash
            capabilities.add("write")

        self.capabilities = capabilities

    def apply_identity(self, identity: dict[str, Any]) -> None:
        data = identity.get("data", identity)
        name = data.get("name") or data.get("username")
        if name:
            self.username = name

        modhash = (
            data.get("modhash")
            or self.modhash
            or _cookie_value(self.cookies, "modhash", "csrf_token")
        )
        if modhash:
            self.modhash = modhash

        self.validation_error = None
        self.refresh_capabilities()
