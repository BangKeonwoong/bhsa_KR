from __future__ import annotations
import logging
from typing import Any, Dict
from flask import jsonify, request
from werkzeug.exceptions import HTTPException


log = logging.getLogger(__name__)


def _json_error(status: int, message: str, code: str) -> tuple[Any, int, Dict[str, str]]:
    payload = {
        "error": code,
        "message": message,
        "path": request.path,
        "method": request.method,
    }
    return jsonify(payload), status, {"Content-Type": "application/json; charset=utf-8"}


def register_error_handlers(app) -> None:
    @app.errorhandler(400)
    def bad_request(e: HTTPException):  # type: ignore[override]
        detail = getattr(e, "description", "잘못된 요청입니다.")
        return _json_error(400, str(detail), "bad_request")

    @app.errorhandler(404)
    def not_found(e: HTTPException):  # type: ignore[override]
        detail = getattr(e, "description", "요청한 리소스를 찾을 수 없습니다.")
        return _json_error(404, str(detail), "not_found")

    @app.errorhandler(405)
    def method_not_allowed(e: HTTPException):  # type: ignore[override]
        detail = getattr(e, "description", "허용되지 않은 메서드입니다.")
        return _json_error(405, str(detail), "method_not_allowed")

    @app.errorhandler(Exception)
    def unhandled_error(e: Exception):  # type: ignore[override]
        # Werkzeug/HTTPException은 위 핸들러들에서 처리됨. 그 외 예외를 여기서 JSON으로 반환.
        log.exception("Unhandled exception: %s %s", request.method, request.path)
        return _json_error(500, "서버 내부 오류가 발생했습니다.", "internal_error")

