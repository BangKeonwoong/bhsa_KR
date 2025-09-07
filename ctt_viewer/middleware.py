from __future__ import annotations
import logging
import time
from flask import g, request, current_app
import uuid
import gzip
try:
    import brotli  # type: ignore
except Exception:  # pragma: no cover
    brotli = None  # type: ignore


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
            # Slow request warn threshold (ms)
            try:
                slow_ms = float(current_app.config.get('SLOW_REQUEST_MS', 1500))
            except Exception:
                slow_ms = 1500.0
            msg = "%s %s status=%s duration_ms=%.1f rid=%s ua=%s"
            args = (request.method, path, getattr(resp, 'status_code', '-'), (dur_ms or 0.0), rid, ua)
            if (dur_ms or 0.0) >= slow_ms:
                logger.warning(msg, *args)
            else:
                logger.info(msg, *args)
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


def _should_compress(resp) -> bool:
    if not bool(current_app.config.get('ENABLE_COMPRESSION', True)):
        return False
    try:
        if request.method not in ('GET','HEAD'):
            return False
    except Exception:
        return False
    # skip already encoded or tiny
    if resp.headers.get('Content-Encoding'):
        return False
    min_size = int(current_app.config.get('COMPRESS_MIN_SIZE', 1024))
    try:
        if resp.direct_passthrough:  # streaming
            return False
    except Exception:
        pass
    data = resp.get_data()
    if not data or len(data) < max(0, min_size):
        return False
    # type filter
    mt = (resp.mimetype or '')
    mlist = str(current_app.config.get('COMPRESS_MIMETYPES', 'application/json')).split(',')
    mlist = [m.strip() for m in mlist if m.strip()]
    ok = any(mt == m or (m.endswith('/*') and mt.startswith(m[:-1])) or (m == 'application/json' and mt.startswith('application/json')) for m in mlist)
    return ok


def init_compression(app) -> None:
    @app.after_request
    def _compress(resp):  # type: ignore[override]
        try:
            if not _should_compress(resp):
                return resp
            ae = request.headers.get('Accept-Encoding', '')
            pick_br = ('br' in ae) and (brotli is not None)
            pick_gz = ('gzip' in ae)
            data = resp.get_data()
            if pick_br:
                try:
                    cdata = brotli.compress(data)  # type: ignore[attr-defined]
                    resp.set_data(cdata)
                    resp.headers['Content-Encoding'] = 'br'
                except Exception:
                    # fallback to gzip
                    pick_br = False
            if (not pick_br) and pick_gz:
                level = int(current_app.config.get('GZIP_LEVEL', 6))
                cdata = gzip.compress(data, compresslevel=max(1, min(9, level)))
                resp.set_data(cdata)
                resp.headers['Content-Encoding'] = 'gzip'
            # If compressed, optionally weaken ETag to keep validator consistent across encodings
            if resp.headers.get('Content-Encoding') and bool(current_app.config.get('WEAK_ETAG_FOR_COMPRESSED', True)):
                et = resp.headers.get('ETag')
                if et and not str(et).startswith('W/'):
                    try:
                        resp.headers['ETag'] = f"W/{et}"
                    except Exception:
                        pass
            # Add Vary header
            vary = resp.headers.get('Vary', '')
            if 'Accept-Encoding' not in vary:
                resp.headers['Vary'] = (vary + ', Accept-Encoding').strip(', ')
            # Update Content-Length
            try:
                resp.headers['Content-Length'] = str(len(resp.get_data()))
            except Exception:
                pass
            return resp
        except Exception:
            return resp
