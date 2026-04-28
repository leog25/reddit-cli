"""HTTP transports for read and write Reddit requests."""

from __future__ import annotations

import random
import time
from typing import Any

import httpx

from reddit_cli.config import RuntimeConfig
from reddit_cli.constants import BASE_URL
from reddit_cli.errors import (
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    RedditAPIError,
    SessionExpiredError,
)
from reddit_cli.fingerprint import BrowserFingerprint
from reddit_cli.session import SessionState


class BaseTransport:
    """Shared retry, throttling, and cookie management."""

    def __init__(
        self,
        session: SessionState,
        *,
        config: RuntimeConfig,
        fingerprint: BrowserFingerprint,
        request_delay: float,
        _transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.session = session
        self.config = config
        self.fingerprint = fingerprint
        self._request_delay = request_delay
        self._max_retries = config.max_retries
        self._last_request_time = 0.0
        self._request_count = 0

        kwargs: dict[str, Any] = dict(
            base_url=BASE_URL,
            headers=self.default_headers(),
            cookies=session.cookies or None,
            follow_redirects=True,
            timeout=httpx.Timeout(config.timeout),
        )
        if _transport is not None:
            kwargs["transport"] = _transport
        self._http = httpx.Client(**kwargs)

    def close(self) -> None:
        self._http.close()

    @property
    def client(self) -> httpx.Client:
        return self._http

    @property
    def request_count(self) -> int:
        return self._request_count

    def default_headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _rate_limit_delay(self) -> None:
        if self._request_delay <= 0:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_delay and self._last_request_time > 0:
            jitter = max(0.0, random.gauss(0.3, 0.15))
            if random.random() < 0.05:
                jitter += random.uniform(2.0, 5.0)
            time.sleep(self._request_delay - elapsed + jitter)

    def _merge_response_cookies(self, resp: httpx.Response) -> None:
        for name, value in resp.cookies.items():
            if not value:
                continue
            self.client.cookies.set(name, value)
            self.session.cookies[name] = value
        self.session.refresh_capabilities()

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        self._rate_limit_delay()
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                resp = self.client.request(method, url, **kwargs)
                self._merge_response_cookies(resp)
                self._request_count += 1
                self._last_request_time = time.time()

                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", 5))
                    if attempt + 1 >= self._max_retries:
                        raise RateLimitError(retry_after=retry_after)
                    time.sleep(retry_after)
                    continue

                if resp.status_code in (500, 502, 503, 504):
                    wait = (2**attempt) + random.uniform(0, 1)
                    time.sleep(wait)
                    continue

                if resp.status_code == 401:
                    raise SessionExpiredError()
                if resp.status_code == 403:
                    raise ForbiddenError()
                if resp.status_code == 404:
                    raise NotFoundError()

                resp.raise_for_status()

                text = resp.text
                if text.strip().startswith("<"):
                    raise RedditAPIError(
                        message="Received HTML instead of JSON"
                        " (possible auth redirect)",
                    )
                if not text.strip():
                    return {}
                return resp.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                wait = (2**attempt) + random.uniform(0, 1)
                time.sleep(wait)

        if last_exc:
            raise RedditAPIError(
                message=f"Request failed after {self._max_retries}"
                f" retries: {last_exc}",
            )
        raise RedditAPIError(
            message=f"Request failed after {self._max_retries} retries",
        )


class ReadTransport(BaseTransport):
    """Transport for low-risk listing and detail requests."""

    def default_headers(self) -> dict[str, str]:
        return self.fingerprint.read_headers()


class WriteTransport(BaseTransport):
    """Transport for state-changing authenticated requests."""

    def default_headers(self) -> dict[str, str]:
        return self.fingerprint.write_headers(modhash=self.session.modhash)

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        if not self.session.can_write:
            raise RedditAPIError(
                message="Session is not write-capable yet;"
                " run 'reddit auth status' to validate",
            )

        headers = dict(kwargs.pop("headers", {}))
        headers.update(self.fingerprint.write_headers(modhash=self.session.modhash))
        kwargs["headers"] = headers

        data = kwargs.get("data")
        if isinstance(data, dict) and self.session.modhash and "uh" not in data:
            kwargs["data"] = {**data, "uh": self.session.modhash}

        return super().request(method, url, **kwargs)
