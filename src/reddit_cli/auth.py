"""Authentication: browser cookie extraction and credential persistence."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time

from pydantic import BaseModel, ConfigDict

from reddit_cli.constants import CONFIG_DIR, CREDENTIAL_FILE, REQUIRED_COOKIES

logger = logging.getLogger(__name__)

CREDENTIAL_TTL_DAYS = 7
_CREDENTIAL_TTL_SECONDS = CREDENTIAL_TTL_DAYS * 86400


class Credential(BaseModel):
    """Reddit session cookies with metadata."""

    model_config = ConfigDict(extra="ignore")

    cookies: dict[str, str] = {}
    source: str = "unknown"
    username: str | None = None
    modhash: str | None = None
    saved_at: float | None = None
    last_verified_at: float | None = None

    @property
    def is_valid(self) -> bool:
        return bool(self.cookies)


def save_credential(credential: Credential) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if credential.saved_at is None:
        credential.saved_at = time.time()
    CREDENTIAL_FILE.write_text(credential.model_dump_json(indent=2))
    try:
        CREDENTIAL_FILE.chmod(0o600)
    except OSError:
        pass  # Windows may not support chmod


def load_credential() -> Credential | None:
    if not CREDENTIAL_FILE.exists():
        return None
    try:
        cred = Credential.model_validate_json(CREDENTIAL_FILE.read_text())
        if not cred.is_valid:
            return None

        if cred.saved_at and (time.time() - cred.saved_at) > _CREDENTIAL_TTL_SECONDS:
            logger.info("Credential older than %d days, attempting refresh", CREDENTIAL_TTL_DAYS)
            fresh = extract_browser_credential()
            if fresh:
                return fresh
            import sys
            logger.warning("Refresh failed; using existing cookies")
            sys.stderr.write(
                "Warning: Using stale cookies (refresh failed)."
                " Run 'reddit auth login' to re-authenticate.\n"
            )

        return cred
    except Exception:
        return None


def clear_credential() -> None:
    if CREDENTIAL_FILE.exists():
        CREDENTIAL_FILE.unlink()


def _is_frozen() -> bool:
    """Detect if running as a compiled binary (Nuitka or PyInstaller)."""
    import sys

    return getattr(sys, "frozen", False) or "__compiled__" in globals()


def extract_browser_credential() -> Credential | None:
    if not _is_frozen() and shutil.which("uv"):
        cred = _extract_subprocess()
        if cred:
            return cred
    cred = _extract_direct()
    if cred:
        return cred
    return _extract_rookiepy()


def _extract_subprocess() -> Credential | None:
    script = (
        "import browser_cookie3, json\n"
        "cookies = {}\n"
        "for fn in [browser_cookie3.chrome, browser_cookie3.firefox,"
        " browser_cookie3.edge, browser_cookie3.brave]:\n"
        "    try:\n"
        "        jar = fn(domain_name='.reddit.com')\n"
        "        for c in jar:\n"
        "            cookies[c.name] = c.value\n"
        "        if cookies:\n"
        "            break\n"
        "    except Exception:\n"
        "        continue\n"
        "if cookies:\n"
        "    print(json.dumps(cookies))\n"
    )
    try:
        result = subprocess.run(
            ["uv", "run", "--with", "browser-cookie3", "python", "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            cookies = json.loads(result.stdout.strip())
            if any(k in cookies for k in REQUIRED_COOKIES):
                cred = Credential(cookies=cookies, source="browser:subprocess")
                save_credential(cred)
                return cred
    except Exception as e:
        logger.debug("Subprocess extraction failed: %s", e)
    return None


def _extract_direct() -> Credential | None:
    try:
        import browser_cookie3
    except ImportError:
        return None

    browsers = [
        browser_cookie3.chrome, browser_cookie3.firefox,
        browser_cookie3.edge, browser_cookie3.brave,
    ]
    for fn in browsers:
        try:
            jar = fn(domain_name=".reddit.com")
            cookies = {c.name: c.value for c in jar}
            if any(k in cookies for k in REQUIRED_COOKIES):
                cred = Credential(cookies=cookies, source=f"browser:{fn.__name__}")
                save_credential(cred)
                return cred
        except Exception:
            continue
    return None


def _extract_rookiepy() -> Credential | None:
    """Try rookiepy (handles Chrome v130+ App-Bound Encryption)."""
    try:
        import rookiepy
    except ImportError:
        return None

    browsers = [
        ("chrome", rookiepy.chrome), ("edge", rookiepy.edge),
        ("firefox", rookiepy.firefox), ("brave", rookiepy.brave),
    ]
    for name, fn in browsers:
        try:
            cookies_list = fn([".reddit.com"])
            cookies = {c["name"]: c["value"] for c in cookies_list}
            if any(k in cookies for k in REQUIRED_COOKIES):
                cred = Credential(cookies=cookies, source=f"browser:{name}")
                save_credential(cred)
                return cred
        except Exception:
            continue
    return None


def get_credential() -> Credential | None:
    cred = load_credential()
    if cred:
        return cred
    cred = extract_browser_credential()
    if cred:
        return cred
    return None
