"""Browser fingerprint helpers for Reddit requests."""

from pydantic import BaseModel, ConfigDict

from reddit_cli.constants import BASE_URL, HEADERS


class BrowserFingerprint(BaseModel):
    """Consistent request fingerprint used across read and write transports."""

    model_config = ConfigDict(frozen=True)

    user_agent: str
    sec_ch_ua: str
    sec_ch_ua_mobile: str
    sec_ch_ua_platform: str
    accept_language: str

    @classmethod
    def chrome133_mac(cls) -> "BrowserFingerprint":
        return cls(
            user_agent=HEADERS["User-Agent"],
            sec_ch_ua=HEADERS["sec-ch-ua"],
            sec_ch_ua_mobile=HEADERS["sec-ch-ua-mobile"],
            sec_ch_ua_platform=HEADERS["sec-ch-ua-platform"],
            accept_language=HEADERS["Accept-Language"],
        )

    def base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "sec-ch-ua": self.sec_ch_ua,
            "sec-ch-ua-mobile": self.sec_ch_ua_mobile,
            "sec-ch-ua-platform": self.sec_ch_ua_platform,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": self.accept_language,
        }

    def read_headers(self) -> dict[str, str]:
        return self.base_headers()

    def write_headers(self, *, modhash: str | None = None) -> dict[str, str]:
        headers = self.base_headers()
        headers.update({
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })
        if modhash:
            headers["x-modhash"] = modhash
        return headers
