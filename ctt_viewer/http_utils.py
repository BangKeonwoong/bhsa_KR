from __future__ import annotations
from flask import Response
import time
from email.utils import formatdate


# HTTP cache header defaults
APP_START_GMT = formatdate(time.time(), usegmt=True)


def cache_control_header(max_age: int, swr: int) -> str:
    return f"public, max-age={max_age}, stale-while-revalidate={swr}, must-revalidate"


def resp_304(etag: str, last_modified: str | None, max_age: int, swr: int) -> Response:
    resp = Response(response="", status=304)
    resp.headers['ETag'] = etag
    resp.headers['Cache-Control'] = cache_control_header(max_age, swr)
    resp.headers['Last-Modified'] = last_modified or APP_START_GMT
    return resp


def resp_json(payload: str, etag: str, last_modified: str | None, max_age: int, swr: int) -> Response:
    resp = Response(response=payload, status=200, mimetype='application/json; charset=utf-8')
    resp.headers['ETag'] = etag
    resp.headers['Cache-Control'] = cache_control_header(max_age, swr)
    resp.headers['Last-Modified'] = last_modified or APP_START_GMT
    return resp


def httpdate(ts: float | None) -> str:
    try:
        return formatdate(ts or time.time(), usegmt=True)
    except Exception:
        return APP_START_GMT

