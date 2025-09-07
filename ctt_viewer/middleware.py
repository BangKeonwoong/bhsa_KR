from __future__ import annotations
import logging
import time
from flask import g, request


def init_request_logging(app) -> None:
    """간단한 접근 로그 남기는 미들웨어.

    - 활성화: app.config['ACCESS_LOG']가 True일 때
    - 제외 경로: app.config['ACCESS_LOG_SKIP'](쉼표 구분 문자열), 기본 '/healthz'
    포맷: 'METHOD PATH status=200 duration_ms=12.3 ua=...'
    """
    if not bool(app.config.get('ACCESS_LOG', True)):
        return
    logger = logging.getLogger('ctt_viewer.access')
    skip_raw = (app.config.get('ACCESS_LOG_SKIP') or '/healthz')
    skip = {p.strip() for p in str(skip_raw).split(',') if p.strip()}

    @app.before_request
    def _start_timer():  # type: ignore[override]
        g._ts = time.perf_counter()

    @app.after_request
    def _log_request(resp):  # type: ignore[override]
        try:
            path = request.path
            if path in skip:
                return resp
            dur_ms = None
            try:
                dur_ms = (time.perf_counter() - getattr(g, '_ts', time.perf_counter())) * 1000.0
            except Exception:
                dur_ms = None
            ua = request.headers.get('User-Agent', '-')
            logger.info(
                "%s %s status=%s duration_ms=%.1f ua=%s",
                request.method,
                path,
                getattr(resp, 'status_code', '-'),
                (dur_ms or 0.0),
                ua,
            )
        finally:
            return resp

