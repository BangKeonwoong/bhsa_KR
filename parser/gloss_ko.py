from __future__ import annotations
import csv
import os
import re
from functools import lru_cache
from typing import Dict, Optional


def _norm_en(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


_LAST_STATUS: Dict[str, object] = {
    'path': None,
    'rows_total': 0,
    'mapped': 0,
    'skipped_short': 0,
    'message': '',
}


@lru_cache(maxsize=1)
def _en_to_ko_map() -> Dict[str, str]:
    """Load English→Korean gloss map using the user's CSV spec.

    - Column 1: English gloss
    - Column 6: Korean gloss
    We store both the exact string and a lowercase variant for robust lookup.
    """
    candidates: list[str] = []
    env_path = os.environ.get("GLOSS_KO_CSV")
    if env_path:
        candidates.append(env_path)
    # fallbacks (optional) — prefer curated filename
    candidates.append(os.path.join("data", "gloss_ko.csv"))
    # also check project root for convenience (common local setup)
    candidates.append(os.path.join("gloss_ko.csv"))
    candidates.append(os.path.join("data", "all_gloss_1_6133_final.csv"))

    path: Optional[str] = None
    for p in candidates:
        if p and os.path.exists(p):
            path = p
            break
    mapping: Dict[str, str] = {}
    if not path:
        _LAST_STATUS.update({'path': None, 'rows_total': 0, 'mapped': 0, 'skipped_short': 0,
                             'message': '한글 gloss CSV를 찾을 수 없습니다. data/gloss_ko.csv 또는 GLOSS_KO_CSV를 확인하세요.'})
        return mapping

    try:
        rows_total = 0
        skipped_short = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if not row:
                    continue
                rows_total += 1
                if len(row) < 6:
                    skipped_short += 1
                    continue
                eng = _norm_en(row[0])
                ko = (row[5] or "").strip()
                if not eng or not ko:
                    continue
                if eng not in mapping:
                    mapping[eng] = ko
                el = eng.lower()
                if el not in mapping:
                    mapping[el] = ko
        _LAST_STATUS.update({'path': path, 'rows_total': rows_total, 'mapped': len(mapping),
                             'skipped_short': skipped_short,
                             'message': '로딩 완료' if mapping else 'CSV 형식을 확인하세요. 1열=영어, 6열=한글'})
    except Exception:
        _LAST_STATUS.update({'path': path, 'rows_total': 0, 'mapped': 0, 'skipped_short': 0,
                             'message': 'CSV 로딩 중 오류가 발생했습니다.'})
        return mapping
    return mapping


def gloss_ko_from_english(english: Optional[str]) -> str:
    """Map an English gloss string to Korean via CSV (col1→col6).

    Tries the full string; if not found, splits on common separators and tries
    parts; also tries removing a leading "to " and lowercase variants.
    """
    mp = _en_to_ko_map()
    if not mp or not english:
        return ""
    def try_one(txt: str) -> Optional[str]:
        txt = _norm_en(txt)
        if not txt:
            return ""
        v = mp.get(txt)
        if v:
            return v
        v = mp.get(txt.lower())
        if v:
            return v
        if txt.lower().startswith("to "):
            base = txt[3:].strip()
            v = mp.get(base) or mp.get(base.lower())
            if v:
                return v
        return ""

    # full string
    v = try_one(english)
    if v:
        return v
    # split and try parts
    for part in re.split(r"[;/,]", english):
        v = try_one(part)
        if v:
            return v
    return ""


def gloss_ko_status() -> Dict[str, object]:
    """현재 한글 gloss 매핑 상태를 반환."""
    # Ensure loader ran at least once to populate status
    try:
        _ = _en_to_ko_map()
    except Exception:
        pass
    return dict(_LAST_STATUS)
