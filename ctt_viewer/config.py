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

    # Request ID
    REQUEST_ID_HEADER: str = os.environ.get("REQUEST_ID_HEADER", "X-Request-ID")

    # CORS (simple built-in toggle)
    ENABLE_CORS: bool = bool(int(os.environ.get("ENABLE_CORS", "0")))
    CORS_ALLOW_ORIGIN: str = os.environ.get("CORS_ALLOW_ORIGIN", "*")
    CORS_ALLOW_METHODS: str = os.environ.get("CORS_ALLOW_METHODS", "GET,OPTIONS")
    CORS_ALLOW_HEADERS: str = os.environ.get("CORS_ALLOW_HEADERS", "Content-Type, If-None-Match, X-Requested-With, X-Request-ID")

    # /api/tree 캐시 정책 (경량/상세)
    TREE_LITE_MAX_AGE: int = int(os.environ.get("TREE_LITE_MAX_AGE", "600"))
    TREE_LITE_SWR: int = int(os.environ.get("TREE_LITE_SWR", "120"))
    TREE_FULL_MAX_AGE: int = int(os.environ.get("TREE_FULL_MAX_AGE", "120"))
    TREE_FULL_SWR: int = int(os.environ.get("TREE_FULL_SWR", "60"))


def apply_env_overrides(app) -> None:
    """Apply simple environment overrides that may affect Flask behavior."""
    # No-op for now; reserved for future flags
    pass
