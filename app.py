from __future__ import annotations
import os
from ctt_viewer import create_app


# 유지 호환용 실행 스크립트: 기존 start_viewer.* 가 app.py를 호출하므로
# 여기서는 앱 팩토리를 통해 Flask 앱을 생성하고 구동만 담당합니다.

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "5001"))
    except Exception:
        port = 5001
    port_file = os.environ.get("PORT_FILE")
    if port_file:
        try:
            with open(port_file, "w") as f:
                f.write(str(port))
        except Exception:
            pass
    debug = os.environ.get("DEBUG", "1") not in ("0", "false", "False")
    app = create_app()
    app.run(host=host, port=port, debug=debug)
