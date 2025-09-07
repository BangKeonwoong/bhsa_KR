from __future__ import annotations
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def static_dir() -> Path:
    return project_root() / "static"


def font_dir() -> Path:
    return project_root() / "font"


def ctt_data_dir() -> Path:
    return project_root() / "data" / "ctt"


def knt_dir() -> Path:
    return project_root() / "KNT"

