from __future__ import annotations
import logging
import os


def _to_level(val: str | int | None, default: int = logging.INFO) -> int:
    if isinstance(val, int):
        return val
    if not val:
        return default
    name = str(val).strip().upper()
    mapping = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'WARN': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET,
    }
    return mapping.get(name, default)


def setup_logging() -> None:
    """Configure application logging based on environment.

    Env vars:
      - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR (default INFO)
      - LOG_FORMAT: printf-style format (default with time/level/name/message)
      - LOG_DATEFMT: datetime format (default %Y-%m-%d %H:%M:%S)
      - WERKZEUG_LOG_LEVEL: override Werkzeug logger level (default = LOG_LEVEL)
    """
    level = _to_level(os.environ.get('LOG_LEVEL'), logging.INFO)
    fmt = os.environ.get('LOG_FORMAT', '[%(asctime)s] %(levelname)s %(name)s: %(message)s')
    datefmt = os.environ.get('LOG_DATEFMT', '%Y-%m-%d %H:%M:%S')

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        root.addHandler(handler)
    root.setLevel(level)

    # Align common noisy loggers with our level
    w_level = _to_level(os.environ.get('WERKZEUG_LOG_LEVEL'), level)
    logging.getLogger('werkzeug').setLevel(w_level)
    # Quiet overly chatty TF internals unless DEBUG requested
    tf_level = logging.DEBUG if level == logging.DEBUG else logging.WARNING
    logging.getLogger('tf').setLevel(tf_level)

