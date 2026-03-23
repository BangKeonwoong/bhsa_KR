from __future__ import annotations
"""BHSA(Text‑Fabric) 데이터 접근 유틸리티.

주요 기능
- 로컬 BHSA 데이터 유무 탐지 및 gloss 기능 확인
- 절/구절 토큰과 gloss 조회, ASCII→히브리 매핑 보조
- clause/clause_atom 기반 트리 생성(TF mother 엣지) 및 세그먼트 분해
"""
from functools import lru_cache
from typing import Dict, List, Tuple, Any, Optional
import json
import copy
from pathlib import Path
import os
import re
import threading

# Lazy import to reduce startup overhead; only load Text-Fabric when needed
Fabric = None  # type: ignore
 
from .gloss_ko import gloss_ko_from_english
from .books import BOOK_LABEL_TO_NAME


def _tf_locations() -> list[str]:
    """Return candidate Text-Fabric data locations.

    Priority:
      1) env TF_LOCATIONS (os.pathsep-separated)
      2) env TF_DATA_DIR or TF_LOCAL_DIR
      3) project-local directories: ./data/text-fabric-data, ./text-fabric-data, ./data/tf, ./tfdata
    """
    env_locs = os.environ.get("TF_LOCATIONS", "").strip()
    locs: list[str] = []
    if env_locs:
        locs.extend([p for p in env_locs.split(os.pathsep) if p])
    for k in ("TF_DATA_DIR", "TF_LOCAL_DIR"):
        v = os.environ.get(k, "").strip()
        if v:
            locs.append(v)
    # project-local (repo root or app bundle Resources/app)
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "data" / "text-fabric-data",
        root / "text-fabric-data",
        root / "data" / "tf",
        root / "tfdata",
        # direct bhsa under app resources (e.g., macOS app: Resources/app/bhsa)
        root / "bhsa",
    ]
    for c in candidates:
        if c.exists():
            locs.append(str(c))
    # de-dup preserve order
    seen = set()
    out: list[str] = []
    for p in locs:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out


def has_local_bhsa_data() -> bool:
    """Return True if BHSA TF data looks available locally.

    Scans candidate locations for a 'bhsa/tf/<ver>' or 'etcbc/bhsa/tf/<ver>' folder
    containing basic TF feature files like 'otext.tf' or 'otype.tf'.
    """
    try:
        locs = _tf_locations()
        for loc in locs:
            base = Path(loc)
            for rp in (base / 'bhsa' / 'tf', base / 'etcbc' / 'bhsa' / 'tf'):
                if not rp.exists():
                    continue
                for vdir in rp.iterdir():
                    if not vdir.is_dir():
                        continue
                    # any of these files indicate a TF dataset is present
                    for marker in ('otext.tf', 'otype.tf', 'oslots.tf'):
                        if (vdir / marker).exists():
                            return True
    except Exception:
        return False
    return False


def has_tf_gloss_feature() -> bool:
    """Return True if a 'gloss.tf' feature file exists in any local TF module path.

    This avoids loading Text-Fabric just to discover gloss availability.
    """
    try:
        for loc in _tf_locations():
            base = Path(loc)
            for rp in (base / 'bhsa' / 'tf', base / 'etcbc' / 'bhsa' / 'tf'):
                if not rp.exists():
                    continue
                for vdir in rp.iterdir():
                    if not vdir.is_dir():
                        continue
                    if (vdir / 'gloss.tf').exists():
                        return True
    except Exception:
        return False
    return False


TF_CORE_FEATURES = "otext otype oslots mother typ rela txt g_word_utf8"
TF_DETAIL_FEATURES_WITH_GLOSS = (
    "otext otype oslots mother typ rela txt g_word_utf8 gloss sp ps nu gn st vs vt "
    "lex g_lex_utf8 function"
)
TF_DETAIL_FEATURES_NO_GLOSS = (
    "otext otype oslots mother typ rela txt g_word_utf8 sp ps nu gn st vs vt "
    "lex g_lex_utf8 function"
)

_TF_STATUS_COND = threading.Condition()
_TF_RUNTIME_STATE = {
    "core_api": None,
    "detail_api": None,
    "core_ready": False,
    "detail_ready": False,
    "core_loading": False,
    "detail_loading": False,
    "phase": "idle",
    "last_error": None,
}


def _tf_module_candidates() -> tuple[list[str], list[str]]:
    """Return `(locations, modules)` ordered to prefer the installed local BHSA."""
    module_candidates = [
        "etcbc/bhsa/tf/2021",
        "etcbc/bhsa/tf/2020",
        "etcbc/bhsa",
        "bhsa/tf/2021",
        "bhsa/tf/2020",
        "bhsa",
    ]
    # If local locations exist, expand candidates based on actual folders
    locs = _tf_locations()
    dynamic: list[str] = []
    for loc in locs:
        try:
            lpath = Path(loc)
            # candidate roots
            for base, rp in (("bhsa", lpath / "bhsa"), ("etcbc/bhsa", lpath / "etcbc" / "bhsa")):
                if rp.exists():
                    # prefer explicit tf versioned dirs if present
                    tfdir = rp / "tf"
                    if tfdir.exists():
                        vers = sorted([p for p in tfdir.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
                        for v in vers:
                            dynamic.append(f"{base}/tf/{v.name}")
                    # also add base itself as fallback
                    dynamic.append(base)
        except Exception:
            pass
    # Merge without duplicates, preserving order (dynamic first so local is preferred)
    seen = set()
    merged: list[str] = []
    for m in dynamic + module_candidates:
        if m not in seen:
            merged.append(m)
            seen.add(m)
    return locs, merged


def _load_tf_from_candidates(feature_string: str):
    """Try all known TF module paths and return the first API that loads."""
    locs, module_candidates = _tf_module_candidates()
    if os.environ.get("TF_DEBUG"):
        print("[TF] locations:", locs)
        print("[TF] module candidates:", module_candidates)
    global Fabric
    if Fabric is None:
        try:
            from tf.fabric import Fabric as _Fabric  # type: ignore
            Fabric = _Fabric
        except Exception:
            return False
    for mod in module_candidates:
        TF = Fabric(modules=[mod], silent="deep", locations=locs or None)
        api = TF.load(feature_string)
        if api:
            if os.environ.get("TF_DEBUG"):
                print("[TF] loaded from:", mod, "features:", feature_string)
            return api
    return False


def _phase_message(phase: str, last_error: Optional[str] = None) -> str:
    if phase == "core":
        return "히브리 원문 feature 로딩 중"
    if phase == "details":
        return "gloss/상세 데이터 준비 중"
    if phase == "ready":
        return "TF 데이터 준비 완료"
    if phase == "error":
        return last_error or "TF 데이터 준비에 실패했습니다."
    return "TF 초기화 대기 중"


def _load_tf_stage(stage: str):
    """Single-flight TF loader for `core` or `details` stages."""
    if stage not in {"core", "details"}:
        raise ValueError(f"Unsupported TF stage: {stage}")

    api_key = "detail_api" if stage == "details" else "core_api"
    ready_key = "detail_ready" if stage == "details" else "core_ready"
    loading_key = "detail_loading" if stage == "details" else "core_loading"
    phase = "details" if stage == "details" else "core"

    with _TF_STATUS_COND:
        api = _TF_RUNTIME_STATE.get(api_key)
        if _TF_RUNTIME_STATE.get(ready_key) and api:
            return api
        if _TF_RUNTIME_STATE.get(loading_key):
            while _TF_RUNTIME_STATE.get(loading_key):
                _TF_STATUS_COND.wait()
            api = _TF_RUNTIME_STATE.get(api_key)
            if _TF_RUNTIME_STATE.get(ready_key) and api:
                return api
            return False
        _TF_RUNTIME_STATE[loading_key] = True
        _TF_RUNTIME_STATE["last_error"] = None
        _TF_RUNTIME_STATE["phase"] = phase

    error_message = None
    try:
        if stage == "details":
            api = _load_tf_from_candidates(TF_DETAIL_FEATURES_WITH_GLOSS)
            if not api:
                api = _load_tf_from_candidates(TF_DETAIL_FEATURES_NO_GLOSS)
        else:
            api = _load_tf_from_candidates(TF_CORE_FEATURES)
        if not api:
            error_message = "BHSA(Text-Fabric) 데이터를 불러오지 못했습니다."
    except Exception as exc:
        api = False
        error_message = str(exc)

    with _TF_STATUS_COND:
        _TF_RUNTIME_STATE[loading_key] = False
        if api:
            _TF_RUNTIME_STATE[api_key] = api
            _TF_RUNTIME_STATE[ready_key] = True
            if stage == "details" and not _TF_RUNTIME_STATE.get("core_ready"):
                _TF_RUNTIME_STATE["core_api"] = api
                _TF_RUNTIME_STATE["core_ready"] = True
            _TF_RUNTIME_STATE["phase"] = "ready"
            _TF_RUNTIME_STATE["last_error"] = None
        else:
            _TF_RUNTIME_STATE["phase"] = "error"
            _TF_RUNTIME_STATE["last_error"] = error_message or "TF load failed"
        _TF_STATUS_COND.notify_all()
        return _TF_RUNTIME_STATE.get(api_key) if api else False


def _spawn_tf_warmup(stage: str) -> None:
    def runner() -> None:
        _load_tf_stage(stage)

    thread = threading.Thread(target=runner, name=f"tf-{stage}-warmup", daemon=True)
    thread.start()


def ensure_tf_warmup(require_details: bool = False) -> None:
    """Kick off background TF loading if it is not already ready/loading."""
    if not has_local_bhsa_data():
        return
    stage = "details" if require_details else "core"
    ready_key = "detail_ready" if require_details else "core_ready"
    loading_key = "detail_loading" if require_details else "core_loading"
    with _TF_STATUS_COND:
        if _TF_RUNTIME_STATE.get(ready_key) or _TF_RUNTIME_STATE.get(loading_key):
            return
    _spawn_tf_warmup(stage)


def get_tf_status(start_warmup: bool = False, require_details: bool = False) -> dict:
    """Return current TF readiness and optionally trigger background warm-up."""
    local_bhsa = bool(has_local_bhsa_data())
    if start_warmup and local_bhsa:
        ensure_tf_warmup(require_details=require_details)
    with _TF_STATUS_COND:
        ready = bool(_TF_RUNTIME_STATE["detail_ready"] if require_details else _TF_RUNTIME_STATE["core_ready"])
        warming = bool(_TF_RUNTIME_STATE["detail_loading"] if require_details else (_TF_RUNTIME_STATE["core_loading"] or _TF_RUNTIME_STATE["detail_loading"]))
        phase = str(_TF_RUNTIME_STATE.get("phase") or "idle")
        if ready and phase not in {"details", "error"}:
            phase = "ready"
        elif require_details and _TF_RUNTIME_STATE["detail_loading"]:
            phase = "details"
        elif (not require_details) and _TF_RUNTIME_STATE["core_loading"]:
            phase = "core"
        last_error = _TF_RUNTIME_STATE.get("last_error")
    if not local_bhsa:
        phase = "idle"
    return {
        "has_local_bhsa": local_bhsa,
        "has_gloss": bool(has_tf_gloss_feature()),
        "ready": bool(ready and local_bhsa),
        "warming": bool(warming),
        "details_ready": bool(_TF_RUNTIME_STATE["detail_ready"] if local_bhsa else False),
        "phase": phase,
        "message": _phase_message(phase, last_error),
        "last_error": last_error,
    }


def _load_tf_core():
    return _load_tf_stage("core")


def _load_tf_details():
    return _load_tf_stage("details")


def _load_tf():
    """Backward-compatible alias for the full/detail TF loader."""
    return _load_tf_details()


def _strip_diacritics(s: str) -> str:
    # 히브리 모음/악센트 제거
    return re.sub(r"[\u0591-\u05BD\u05BF-\u05C7]", "", s)


@lru_cache(maxsize=2048)
def get_verse_tokens(book_label: str, chapter: int, verse: int) -> List[str]:
    api = _load_tf_core()
    if not api:
        return []
    F, L, T = api.F, api.L, api.T
    book_name = BOOK_LABEL_TO_NAME.get(book_label.upper())
    if not book_name:
        return []
    # 이름 후보 생성: 공백→언더스코어 버전 포함
    candidates = []
    candidates.append(book_name)
    if ' ' in book_name:
        candidates.append(book_name.replace(' ', '_'))
    # 직접 섹션으로 접근 (후보 순회)
    v = None
    for cand in candidates:
        v = T.nodeFromSection((cand, chapter, verse))
        if v:
            break
    if not v:
        return []
    tokens: List[str] = []
    for w in L.d(v, otype="word"):
        val = None
        if hasattr(F, 'g_word_utf8'):
            val = F.g_word_utf8.v(w)
        if not val:
            # pretty Hebrew with vowels from otext
            try:
                val = T.text(w, fmt='text-orig-full')
            except Exception:
                val = T.text(w)
        tokens.append(val)
    return tokens


def verse_text(book_label: str, chapter: int, verse: int) -> str:
    return " ".join(get_verse_tokens(book_label, chapter, verse))


def verse_gloss(book_label: str, chapter: int, verse: int) -> str:
    api = _load_tf_details()
    if not api:
        return ""
    F, L, T = api.F, api.L, api.T
    book_name = BOOK_LABEL_TO_NAME.get(book_label.upper())
    if not book_name:
        return ""
    # try names with and without underscore
    vNode = None
    for cand in [book_name, book_name.replace(' ', '_')]:
        try:
            vNode = T.nodeFromSection((cand, chapter, verse))
        except Exception:
            vNode = None
        if vNode:
            break
    if not vNode:
        return ""
    glosses: List[str] = []
    for w in L.d(vNode, otype="word"):
        gfeat = getattr(F, 'gloss', None)
        gval = gfeat.v(w) if gfeat else ''
        if not gval and hasattr(L, 'u') and gfeat:
            try:
                lex = (L.u(w, otype='lex') or [None])[0]
                if lex:
                    gval = gfeat.v(lex) or ''
            except Exception:
                pass
        glosses.append(gval or '')
    return " ".join(glosses).strip()


def map_ascii_tokens_to_bhsa(book_label: str, chapter: int, verse: int, ascii_tokens: List[str]) -> List[str]:
    """아주 단순한 정렬: BHSA 토큰(g_word_utf8)의 자모만 추출해 선형 스캔으로 매칭.
    실패 시 해당 토큰은 원문 유지.
    """
    bhsa = get_verse_tokens(book_label, chapter, verse)
    bhsa_stripped = [_strip_diacritics(t) for t in bhsa]

    # ASCII→히브리(무모음)로 이미 변환된 토큰을 기대함.
    out: List[str] = []
    i = 0
    for tok in ascii_tokens:
        base = _strip_diacritics(tok)
        taken = None
        while i < len(bhsa_stripped):
            if bhsa_stripped[i].replace("־", "") .startswith(base[:2]) or base.startswith(bhsa_stripped[i][:2]):
                taken = bhsa[i]
                i += 1
                break
            i += 1
        out.append(taken or tok)
    return out


def parse_chapter_tf(book_label: str, chapter: int, title: str, include_details: bool = False) -> Dict[str, Any]:
    """주어진 책/장에 대해 TF의 clause_atom을 모아 mother 엣지로 트리 구성.

    include_details=False 일 때는 토큰/글로스/기능 라벨을 제외한 경량 트리를 반환.
    """
    api = _load_tf_details() if include_details else _load_tf_core()
    if not api:
        raise RuntimeError("BHSA API not available")
    F, L, T, E = api.F, api.L, api.T, api.E

    book_name = BOOK_LABEL_TO_NAME.get(book_label.upper())
    if not book_name:
        raise ValueError(f"Unsupported book label: {book_label}")

    root: Dict[str, Any] = {"id": "root", "name": title, "source": "tf", "children": []}

    # 1) 대상 장의 verse를 순회하여 clause_atom 수집
    in_scope_set: set[int] = set()
    vnum = 1
    gap = 0
    while True:
        vNode = None
        for cand in [book_name, book_name.replace(' ', '_')]:
            try:
                vNode = T.nodeFromSection((cand, chapter, vnum))
            except Exception:
                vNode = None
            if vNode:
                break
        if not vNode:
            gap += 1
            if gap >= 2:
                break
        else:
            gap = 0
            for c in L.d(vNode, otype="clause_atom"):
                in_scope_set.add(c)
        vnum += 1
    in_scope = sorted(in_scope_set)

    if not in_scope:
        return root

    # 2) 노드 메타 구성
    nodes: Dict[int, Dict[str, Any]] = {}
    # phrase 기능을 수집하기 위한 매핑
    BHSA_FUNC_MAP = {
        'Subj': 'Su', 'Pred': 'Pr', 'Objc': 'Ob', 'Cmpl': 'Cmpl', 'Adju': 'Adju', 'Attr': 'Attr',
        'PreC': 'Pr', 'Resu': 'Resu', 'Spec': 'Spec', 'RgRc': 'RgRc', 'Frnt': 'Frnt', 'Time': 'Time'
    }

    for c in in_scope:
        words = L.d(c, otype="word")
        b, ch, v = T.sectionFromNode(words[0])
        verse_label = f"{book_label} {ch:02d},{v:02d}"
        parts: List[str] = []
        gloss_parts: List[str] = []  # 영어 gloss summary
        gloss_ko_parts: List[str] = []  # 한글 gloss summary
        token_list: List[Dict[str, Any]] = []
        for w in words:
            if hasattr(F, 'g_word_utf8'):
                val = F.g_word_utf8.v(w)
            else:
                try:
                    val = T.text(w, fmt='text-orig-full')
                except Exception:
                    val = T.text(w)
            parts.append(val)
            # 영어 gloss 및 한글 gloss 요약(가능할 때만)
            g = ''
            if hasattr(F, 'gloss'):
                try:
                    g = F.gloss.v(w) or ''
                except Exception:
                    g = ''
                if not g:
                    try:
                        lex = (L.u(w, otype='lex') or [None])[0]
                        if lex:
                            g = F.gloss.v(lex) or ''
                    except Exception:
                        g = ''
            if g:
                gloss_parts.append(g)
                gko = gloss_ko_from_english(g)
                if gko:
                    gloss_ko_parts.append(gko)
            if include_details:
                token = {"w": val, "wid": w}
                if g:
                    token["gloss"] = g
                if gko:
                    token["gloss_ko"] = gko
                for feat in ("sp","ps","nu","gn","st","vs","vt"):
                    if hasattr(F, feat):
                        token[feat] = getattr(F, feat).v(w) or ""
                token_list.append(token)
        if include_details and hasattr(F, 'function'):
            func_set = set()
            for ph in L.d(c, otype='phrase'):
                fval = F.function.v(ph)
                if fval:
                    tag = BHSA_FUNC_MAP.get(fval, fval)
                    func_set.add(tag)
            for pha in L.d(c, otype='phrase_atom'):
                fval = F.function.v(pha)
                if fval:
                    tag = BHSA_FUNC_MAP.get(fval, fval)
                    func_set.add(tag)
        text = " ".join(parts)
        # 각 히브리 단어별 gloss는 ' | '로 결합하고, 한글 gloss의 '/'는 ';'로 치환
        gloss_text = " | ".join(gloss_parts) if gloss_parts else ""
        gloss_ko_text = " | ".join((p.replace('/', ';') for p in gloss_ko_parts)) if gloss_ko_parts else ""
        typ = F.typ.v(c) or ""
        # clause_atom에는 rela가 비어있는 경우가 많아 상위 clause에서 보완
        rela = F.rela.v(c) or ""
        if not rela:
            try:
                up_clause = (L.u(c, otype='clause') or [None])[0]
            except Exception:
                up_clause = None
            if up_clause:
                rela = F.rela.v(up_clause) or ""
        text_type = F.txt.v(c) or ""
        name = f"{verse_label} – {typ} – {text}"
        node = {
            "id": c,
            "name": name,
            "verse": verse_label,
            "pn": "",
            "ctype": typ,
            "text": text,
            "rela": rela,
            "text_type": text_type if text_type in ("N","D","Q") else "",
            "children": [],
        }
        # 요약 gloss 문자열은 항상 제공(가능한 경우)
        if gloss_text:
            node["gloss"] = gloss_text
        if gloss_ko_text:
            node["gloss_ko"] = gloss_ko_text
        if include_details:
            node["tokens"] = token_list
            node["funcs"] = sorted(func_set)
        nodes[c] = node

    # 3) 모‑자 연결 (mother 엣지, 범위 밖이면 루트에)
    index_in_scope = set(in_scope)
    for c in in_scope:
        # 가장 가까운 in-scope 모를 찾기 위해 위로 상승
        mom = (E.mother.f(c) or [None])[0]
        seen = set()
        while mom and mom not in index_in_scope and mom not in seen:
            seen.add(mom)
            mom = (E.mother.f(mom) or [None])[0]
        if mom in index_in_scope:
            nodes[mom]["children"].append(nodes[c])
        else:
            root["children"].append(nodes[c])

    return root


# --- Cached variant for faster repeat loads ---
@lru_cache(maxsize=64)
def _cache_tf_tree(book_label: str, chapter: int, include_details: bool) -> str:
    """Cache TF parse result as JSON text with a canonical title; caller may override name."""
    # Use an internal title to build; caller will replace root name
    canonical_title = f"{BOOK_LABEL_TO_NAME.get(book_label.upper(), book_label)} {chapter}"
    data = parse_chapter_tf(book_label, chapter, canonical_title, include_details)
    return json.dumps(data, ensure_ascii=False)


def parse_chapter_tf_cached(book_label: str, chapter: int, title: str, include_details: bool = False) -> Dict[str, Any]:
    """Return a fresh copy of a cached TF tree, updating root title."""
    s = _cache_tf_tree(book_label, chapter, include_details)
    data = json.loads(s)
    if isinstance(data, dict) and data.get('id') == 'root':
        data['name'] = title
    return data


def node_details(node_id: int) -> Dict[str, Any]:
    """주어진 TF 노드(clause/clause_atom)의 상세(토큰/글로스/기능 등)를 반환."""
    api = _load_tf_details()
    if not api:
        return {}
    F, L, T = api.F, api.L, api.T
    otype = api.F.otype.v(node_id) if hasattr(api, 'F') and hasattr(api.F, 'otype') else None
    if otype not in ('clause', 'clause_atom'):
        # 상위 clause_atom 시도
        try:
            up = (L.u(node_id, otype='clause_atom') or [None])[0]
        except Exception:
            up = None
        if up:
            node_id = up
        else:
            return {}
    # 기본 메타
    words = L.d(node_id, otype='word') or []
    parts: List[str] = []
    gloss_parts: List[str] = []
    token_list: List[Dict[str, Any]] = []
    for w in words:
        if hasattr(F, 'g_word_utf8'):
            val = F.g_word_utf8.v(w)
        else:
            try:
                val = T.text(w, fmt='text-orig-full')
            except Exception:
                val = T.text(w)
        parts.append(val)
        g = ''
        if hasattr(F, 'gloss'):
            try:
                g = F.gloss.v(w) or ''
            except Exception:
                g = ''
        if not g and hasattr(L, 'u') and hasattr(F, 'gloss'):
            try:
                lex = (L.u(w, otype='lex') or [None])[0]
                if lex:
                    g = F.gloss.v(lex) or ''
            except Exception:
                g = ''
        gko = gloss_ko_from_english(g) if g else ''
        tok: Dict[str, Any] = {"w": val, "wid": w}
        for feat in ('sp','ps','nu','gn','st','vs','vt'):
            if hasattr(F, feat):
                tok[feat] = getattr(F, feat).v(w) or ''
        if g:
            tok['gloss'] = g
        if gko:
            tok['gloss_ko'] = gko
        token_list.append(tok)
    # 기능, 관계, 텍스트 유형
    func_set = set()
    if hasattr(F, 'function'):
        try:
            for ph in L.d(node_id, otype='phrase') or []:
                fval = F.function.v(ph)
                if fval:
                    func_set.add(fval)
            for pha in L.d(node_id, otype='phrase_atom') or []:
                fval = F.function.v(pha)
                if fval:
                    func_set.add(fval)
        except Exception:
            pass
    rela = F.rela.v(node_id) if hasattr(F, 'rela') else ''
    if not rela:
        try:
            up_clause = (L.u(node_id, otype='clause') or [None])[0]
        except Exception:
            up_clause = None
        if up_clause and hasattr(F, 'rela'):
            rela = F.rela.v(up_clause) or ''
    text_type = F.txt.v(node_id) if hasattr(F, 'txt') else ''
    return {
        'id': node_id,
        'text': ' '.join(parts),
        'tokens': token_list,
        'gloss': ' '.join(x for x in (t.get('gloss') for t in token_list) if x),
        'gloss_ko': ' '.join(x for x in (t.get('gloss_ko') for t in token_list) if x),
        'funcs': sorted(func_set),
        'rela': rela,
        'text_type': text_type if text_type in ('N','D','Q') else ''
    }


def typ_stats(book_label: str | None = None, max_chapters: int | None = None) -> Dict[str, int]:
    """Enumerate TF clause/clause_atom typ values with counts.

    - If book_label is provided (e.g., 'GEN'), restrict to that book; otherwise iterate all books in BOOK_LABEL_TO_NAME.
    - For each chapter, iterate verses until 2 consecutive gaps (same heuristic as elsewhere).
    - Counts typ on clause_atom nodes (fallback to clause if clause_atom empty).
    """
    api = _load_tf_core()
    if not api:
        return {}
    F, L, T = api.F, api.L, api.T

    books = [book_label] if book_label else list(BOOK_LABEL_TO_NAME.keys())
    counts: Dict[str, int] = {}
    for bl in books:
        book_name = BOOK_LABEL_TO_NAME.get(bl)
        if not book_name:
            continue
        ch = 1
        gaps = 0
        chapters_seen = 0
        while True:
            vNode = None
            for cand in [book_name, book_name.replace(' ', '_')]:
                try:
                    vNode = T.nodeFromSection((cand, ch, 1))
                except Exception:
                    vNode = None
                if vNode:
                    break
            if not vNode:
                gaps += 1
                if gaps >= 2:
                    break
                ch += 1
                continue
            gaps = 0
            chapters_seen += 1
            if max_chapters and chapters_seen > max_chapters:
                break
            # collect all clause_atoms in this chapter
            # find last verse number by scanning until gap
            v = 1
            while True:
                vNode = None
                for cand in [book_name, book_name.replace(' ', '_')]:
                    try:
                        vNode = T.nodeFromSection((cand, ch, v))
                    except Exception:
                        vNode = None
                    if vNode:
                        break
                if not vNode:
                    break
                for c in L.d(vNode, otype="clause_atom"):
                    tval = F.typ.v(c) or ''
                    counts[tval] = counts.get(tval, 0) + 1
                v += 1
            ch += 1
    return counts


def _phrase_category_ko(function_val: str, tokens: list[dict]) -> tuple[str, str]:
    """구 카테고리 판별: function 우선, 없을 때 품사 기반 보완.

    반환 (cat_key, label_ko)
    """
    f = (function_val or '').strip()
    m = f[:4]
    if m == 'Subj':
        return 'subj', '주어구'
    if m == 'Pred' or m == 'PreC':
        return 'pred', '서술구'
    if m == 'Objc':
        return 'obj', '목적어구'
    if m == 'Cmpl':
        return 'cmpl', '보어구'
    if m == 'Adju':
        return 'adju', '수식구'
    if m == 'Attr':
        return 'attr', '관형구'
    if m == 'Time':
        return 'time', '시간구'
    if m == 'Resu':
        return 'resu', '결과구'
    if m == 'Spec':
        return 'spec', '특수구'
    if m == 'Frnt':
        return 'frnt', '전면제시구'
    # function 없을 때 품사 기반 추정
    has_prep = any((t.get('sp') or '').lower() == 'prep' for t in tokens)
    has_conj = any((t.get('sp') or '').lower() == 'conj' for t in tokens)
    if has_conj and not has_prep:
        return 'conj', '접속구'
    if has_prep:
        return 'prep', '전치사구'
    return 'other', '기타 구'


def get_phrase_segments(node_id: int, level: str = 'phrase') -> list[dict]:
    """Return phrase(또는 phrase_atom) 세그먼트 목록 for a given clause/clause_atom node id.

    Each segment: { text, gloss_ko, function, cat, cat_ko, tokens:[{w, sp, gloss_ko}] }
    """
    api = _load_tf_details()
    if not api:
        return []
    F, L, T = api.F, api.L, api.T
    # 유효 노드 타입 확인: clause 또는 clause_atom만 허용
    # 노드 타입 확인 (F.otype)
    otype = api.F.otype.v(node_id) if hasattr(api, 'F') and hasattr(api.F, 'otype') else None
    if otype not in ('clause', 'clause_atom'):
        # clause_atom 자식일 수도 있으니, 상위 clause_atom을 시도
        try:
            up = (L.u(node_id, otype='clause_atom') or [None])[0]
        except Exception:
            up = None
        if up:
            node_id = up
        else:
            return []
    # 대상 레벨 선택
    lev = 'phrase' if (level or 'phrase') == 'phrase' else 'phrase_atom'
    segs: list[dict] = []
    try:
        units = L.d(node_id, otype=lev) or []
    except Exception:
        units = []
    # 일부 데이터에서는 phrase/phrase_atom이 clause에만 매달려 있음 → 상위 clause에서 범위 필터링
    if not units:
        try:
            up_clause = (L.u(node_id, otype='clause') or [None])[0]
        except Exception:
            up_clause = None
        if up_clause:
            try:
                # 이 clause_atom의 단어 범위
                words_in_ca = set(L.d(node_id, otype='word') or [])
                cand_units = L.d(up_clause, otype=lev) or []
                units = []
                for u in cand_units:
                    uw = set(L.d(u, otype='word') or [])
                    if uw & words_in_ca:
                        units.append(u)
            except Exception:
                pass
    for ph in units:
        words = L.d(ph, otype='word') or []
        tokens: list[dict] = []
        parts: list[str] = []
        gko_parts: list[str] = []
        for w in words:
            if hasattr(F, 'g_word_utf8'):
                wtxt = F.g_word_utf8.v(w)
            else:
                try:
                    wtxt = T.text(w, fmt='text-orig-full')
                except Exception:
                    wtxt = T.text(w)
            parts.append(wtxt)
            # gloss ko
            g = ''
            if hasattr(F, 'gloss'):
                try:
                    g = F.gloss.v(w) or ''
                except Exception:
                    g = ''
            gko = gloss_ko_from_english(g) if g else ''
            if gko:
                gko_parts.append(gko)
            tok = { 'w': wtxt, 'wid': w }
            for feat in ('sp','ps','nu','gn','st','vs','vt'):
                if hasattr(F, feat):
                    tok[feat] = getattr(F, feat).v(w) or ''
            if g:
                tok['gloss'] = g
            if gko:
                tok['gloss_ko'] = gko
            tokens.append(tok)
        func = ''
        if hasattr(F, 'function'):
            try:
                func = F.function.v(ph) or ''
            except Exception:
                func = ''
        # phrase_atom일 때 function 공백이면 상위 phrase의 function을 보완 사용
        if (not func) and lev == 'phrase_atom' and hasattr(L, 'u') and hasattr(F, 'function'):
            try:
                up_ph = (L.u(ph, otype='phrase') or [None])[0]
                if up_ph:
                    func = F.function.v(up_ph) or func
            except Exception:
                pass
        cat, cat_ko = _phrase_category_ko(func, tokens)
        segs.append({
            'text': ' '.join(parts),
            'gloss_ko': ' | '.join(x.replace('/', ';') for x in gko_parts if x),
            'function': func,
            'cat': cat,
            'cat_ko': cat_ko,
            'tokens': tokens,
        })
    return segs
