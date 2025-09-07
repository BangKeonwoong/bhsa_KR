from __future__ import annotations
from pathlib import Path
import os


def _package_dir() -> Path:
    return Path(__file__).resolve().parent


def project_root() -> Path:
    """Return repository root when running from source; otherwise site-packages.

    For packaged installs this returns the parent of the package dir, which is
    good enough for optional fallbacks.
    """
    return _package_dir().parent


def static_dir() -> Path:
    # 1) Explicit override via env
    e = os.environ.get('STATIC_DIR')
    if e and Path(e).exists():
        return Path(e)
    # 2) Packaged static next to module
    cand = _package_dir() / "static"
    if cand.exists():
        return cand
    # 3) Repo root
    return project_root() / "static"


def font_dir() -> Path:
    e = os.environ.get('FONT_DIR')
    if e and Path(e).exists():
        return Path(e)
    cand = _package_dir() / "font"
    if cand.exists():
        return cand
    return project_root() / "font"


def ctt_data_dir() -> Path:
    e = os.environ.get('DATA_CTT_DIR')
    if e and Path(e).exists():
        return Path(e)
    return project_root() / "data" / "ctt"


def knt_dir() -> Path:
    e = os.environ.get('KNT_DIR')
    if e and Path(e).exists():
        return Path(e)
    return project_root() / "KNT"
