from __future__ import annotations
import logging
import time
from flask import g, request, current_app
import uuid


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
            # Request ID attach/propagate
            req_id_header = app.config.get('REQUEST_ID_HEADER', 'X-Request-ID')
            rid = request.headers.get(req_id_header) or getattr(g, '_request_id', None)
            if not rid:
                rid = str(uuid.uuid4())
                g._request_id = rid
            try:
                resp.headers[req_id_header] = rid
            except Exception:
                pass
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
                "%s %s status=%s duration_ms=%.1f rid=%s ua=%s",
                request.method,
                path,
                getattr(resp, 'status_code', '-'),
                (dur_ms or 0.0),
                rid,
                ua,
            )
        finally:
            return resp


def init_request_id(app) -> None:
    """Request ID 생성 및 g에 저장 (before_request)."""
    @app.before_request
    def _assign_request_id():  # type: ignore[override]
        hdr = app.config.get('REQUEST_ID_HEADER', 'X-Request-ID')
        rid = request.headers.get(hdr)
        if not rid:
            rid = str(uuid.uuid4())
        g._request_id = rid


def init_cors(app) -> None:
    """아주 간단한 CORS 추가(필요시 flask-cors로 대체 가능)."""
    if not bool(app.config.get('ENABLE_CORS', False)):
        return
    allow_origin = app.config.get('CORS_ALLOW_ORIGIN', '*')
    allow_methods = app.config.get('CORS_ALLOW_METHODS', 'GET,OPTIONS')
    allow_headers = app.config.get('CORS_ALLOW_HEADERS', 'Content-Type, If-None-Match, X-Requested-With, X-Request-ID')

    @app.after_request
    def _add_cors_headers(resp):  # type: ignore[override]
        try:
            resp.headers['Access-Control-Allow-Origin'] = allow_origin
            resp.headers['Access-Control-Allow-Methods'] = allow_methods
            resp.headers['Access-Control-Allow-Headers'] = allow_headers
        finally:
            return resp
