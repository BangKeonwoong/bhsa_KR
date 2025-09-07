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

    # 응답 압축
    ENABLE_COMPRESSION: bool = bool(int(os.environ.get("ENABLE_COMPRESSION", "1")))
    COMPRESS_MIN_SIZE: int = int(os.environ.get("COMPRESS_MIN_SIZE", "1024"))
    GZIP_LEVEL: int = int(os.environ.get("GZIP_LEVEL", "6"))
    # 쉼표 구분 mimetype 목록 (접두 일치 허용)
    COMPRESS_MIMETYPES: str = os.environ.get("COMPRESS_MIMETYPES", "application/json")


def _set_if_env(app, key: str, cast):
    import os as _os
    if key in _os.environ:
        try:
            app.config[key] = cast(_os.environ.get(key))
        except Exception:
            try:
                app.config[key] = _os.environ.get(key)
            except Exception:
                pass


def apply_env_overrides(app) -> None:
    """Apply environment overrides at runtime for easier testing/config."""
    for k in (
        'CACHE_MAX_AGE','CACHE_SWR','TREE_LITE_MAX_AGE','TREE_LITE_SWR',
        'TREE_FULL_MAX_AGE','TREE_FULL_SWR','COMPRESS_MIN_SIZE','GZIP_LEVEL'
    ):
        _set_if_env(app, k, lambda v: int(str(v)))
    for k in (
        'ENABLE_CORS','ACCESS_LOG','ENABLE_COMPRESSION'
    ):
        _set_if_env(app, k, lambda v: bool(int(str(v))))
    for k in (
        'REQUEST_ID_HEADER','CORS_ALLOW_ORIGIN','CORS_ALLOW_METHODS','CORS_ALLOW_HEADERS','COMPRESS_MIMETYPES'
    ):
        _set_if_env(app, k, str)
