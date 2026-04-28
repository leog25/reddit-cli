"""Runtime configuration for transport, auth, and anti-detection defaults."""

from pydantic import BaseModel, ConfigDict


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    timeout: float = 30.0
    read_request_delay: float = 0.5
    write_request_delay: float = 2.5
    max_retries: int = 3
    status_check_timeout: float = 10.0


DEFAULT_CONFIG = RuntimeConfig()
