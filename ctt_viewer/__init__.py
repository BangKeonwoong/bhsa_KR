from __future__ import annotations
import os
from pathlib import Path
from flask import Flask
from .logging_config import setup_logging
from .config import BaseConfig, apply_env_overrides
from .errors import register_error_handlers
from .middleware import init_request_logging


def project_root() -> Path:
    """Return the repository root (one level above this package)."""
    return Path(__file__).resolve().parents[1]


def create_app() -> Flask:
    """Application factory for the CTT/BHSA viewer.

    - Sets up static/asset directories using absolute paths
    - Registers API routes via blueprint
    """
    # Initialize logging early so Flask/Werkzeug follow our settings
    setup_logging()
    root = project_root()
    static_dir = root / "static"
    app = Flask(
        __name__,
        static_url_path="",
        static_folder=str(static_dir),
    )
    app.config.from_object(BaseConfig)
    apply_env_overrides(app)

    # Middlewares & error handlers
    init_request_logging(app)
    register_error_handlers(app)

    # Register routes
    from .api import api_bp, register_misc_routes  # lazy import
    app.register_blueprint(api_bp)
    register_misc_routes(app, root)

    return app
