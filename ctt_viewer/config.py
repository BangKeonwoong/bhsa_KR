from __future__ import annotations
import os


class BaseConfig:
    """Default configuration loaded into Flask app.config.

    Values may be overridden via environment variables.
    """
    # HTTP cache
    CACHE_MAX_AGE: int = int(os.environ.get("CACHE_MAX_AGE", "300"))
    CACHE_SWR: int = int(os.environ.get("CACHE_SWR", "60"))

    # Flask built-ins (optional overrides)
    JSON_AS_ASCII: bool = False

    # Access log
    ACCESS_LOG: bool = bool(int(os.environ.get("ACCESS_LOG", "1")))
    ACCESS_LOG_SKIP: str = os.environ.get("ACCESS_LOG_SKIP", "/healthz")


def apply_env_overrides(app) -> None:
    """Apply simple environment overrides that may affect Flask behavior."""
    # No-op for now; reserved for future flags
    pass
