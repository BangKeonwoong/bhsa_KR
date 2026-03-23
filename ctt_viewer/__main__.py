from __future__ import annotations
import os
from . import create_app


def main() -> None:
    app = create_app()
    host = os.environ.get("HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "5001"))
    except Exception:
        port = 5001
    debug = os.environ.get("DEBUG", "0") not in ("0", "false", "False")
    app.run(host=host, port=port, debug=debug, use_reloader=debug)


if __name__ == "__main__":
    main()
