from __future__ import annotations
from flask import Flask, jsonify, request, send_from_directory
import os
from pathlib import Path
from parser.ctt_parser import parse_ctt, parse_ctt_cached, enumerate_ctt_ctypes
from parser.bhsa import parse_chapter_tf, parse_chapter_tf_cached, typ_stats, get_phrase_segments, has_local_bhsa_data, has_tf_gloss_feature, node_details
from parser.books import BOOK_LABEL_TO_NAME, BOOK_DIR, resolve_book_label, KNT_LABEL_TO_KO
from parser.gloss_ko import gloss_ko_status
from typing import Optional
from functools import lru_cache
import json
import hashlib
import time
from email.utils import formatdate
import re

app = Flask(__name__, static_url_path='', static_folder='static')

DATA_DIR = Path("data/ctt")
KNT_DIR = Path("KNT")

"""Flask server exposing endpoints for the CTT/BHSA viewer."""

# HTTP cache header defaults
APP_START_GMT = formatdate(time.time(), usegmt=True)
DEFAULT_MAX_AGE = int(os.environ.get("CACHE_MAX_AGE", "300"))
DEFAULT_SWR = int(os.environ.get("CACHE_SWR", "60"))

def _cache_control(max_age: int | None = None, swr: int | None = None) -> str:
    return f"public, max-age={max_age or DEFAULT_MAX_AGE}, stale-while-revalidate={swr or DEFAULT_SWR}, must-revalidate"

def _resp_304(etag: str, last_modified: str | None = None, max_age: int | None = None, swr: int | None = None):
    resp = app.response_class(response="", status=304)
    resp.headers['ETag'] = etag
    resp.headers['Cache-Control'] = _cache_control(max_age, swr)
    resp.headers['Last-Modified'] = last_modified or APP_START_GMT
    return resp

def _resp_json(payload: str, etag: str, last_modified: str | None = None, max_age: int | None = None, swr: int | None = None):
    resp = app.response_class(response=payload, status=200, mimetype='application/json; charset=utf-8')
    resp.headers['ETag'] = etag
    resp.headers['Cache-Control'] = _cache_control(max_age, swr)
    resp.headers['Last-Modified'] = last_modified or APP_START_GMT
    return resp

def _httpdate(ts: float) -> str:
    try:
        return formatdate(ts, usegmt=True)
    except Exception:
        return APP_START_GMT

def _latest_ctt_mtime(path: Path | None) -> Optional[str]:
    try:
        if path and path.exists():
            return _httpdate(path.stat().st_mtime)
    except Exception:
        pass
    return None

def _latest_tf_mtime() -> Optional[str]:
    # Approximate: scan common TF locations for key files and take max mtime
    roots: list[str] = []
    env_locs = os.environ.get("TF_LOCATIONS", "").strip()
    if env_locs:
        roots.extend([p for p in env_locs.split(os.pathsep) if p])
    for k in ("TF_DATA_DIR", "TF_LOCAL_DIR"):
        v = os.environ.get(k, "").strip()
        if v:
            roots.append(v)
    proj = Path(__file__).resolve().parents[1]
    for c in [proj/"data"/"text-fabric-data", proj/"text-fabric-data", proj/"data"/"tf", proj/"tfdata", proj/"bhsa"]:
        if c.exists():
            roots.append(str(c))
    seen = set(); locs: list[str] = []
    for r in roots:
        if r not in seen:
            seen.add(r); locs.append(r)
    latest = 0.0
    for loc in locs:
        try:
            lpath = Path(loc)
            for rp in (lpath/"bhsa"/"tf", lpath/"etcbc"/"bhsa"/"tf"):
                if not rp.exists():
                    continue
                for vdir in rp.iterdir():
                    if not vdir.is_dir():
                        continue
                    for nm in ("otext.tf","otype.tf","oslots.tf","gloss.tf"):
                        f = vdir / nm
                        if f.exists():
                            try:
                                mt = f.stat().st_mtime
                                if mt > latest:
                                    latest = mt
                            except Exception:
                                pass
        except Exception:
            continue
    if latest > 0:
        return _httpdate(latest)
    return None


def _latest_ctt_root_mtime(root: Path | None = None) -> str | None:
    try:
        base = root or DATA_DIR
        if not base.exists():
            return None
        latest = 0.0
        for dirpath, dirnames, filenames in os.walk(base):
            for fn in filenames:
                if not fn.endswith('.CTT'):
                    continue
                f = Path(dirpath) / fn
                try:
                    mt = f.stat().st_mtime
                    if mt > latest:
                        latest = mt
                except Exception:
                    continue
        if latest > 0:
            return _httpdate(latest)
    except Exception:
        return None
    return None


def read_knt_verse(book_label: str, chapter: int, verse: int) -> Optional[str]:
    """Read KNT verse text from Markdown files under KNT/<책>/CC.md.

    Lines look like: '- 3: 텍스트...'
    Returns the verse text without the leading number or None if not found.
    """
    ko_dir = KNT_LABEL_TO_KO.get(book_label.upper())
    if not ko_dir:
        return None
    path = KNT_DIR / ko_dir / f"{chapter:02d}.md"
    if not path.exists():
        return None
    pat = re.compile(r"^\s*-\s*(\d+)\s*:\s*(.*)$")
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                m = pat.match(line)
                if not m:
                    continue
                try:
                    v = int(m.group(1))
                except Exception:
                    continue
                if v == int(verse):
                    return m.group(2).strip()
    except Exception:
        return None
    return None


@lru_cache(maxsize=128)
def _tree_payload_cached(book_param: str, chapter: int, requested: str, lite: bool, bhsa_avail: bool) -> tuple[str, str, Optional[str]]:
    """Build and cache final /api/tree JSON payload and its ETag.

    Keyed by request parameters and BHSA availability. Parser-level caches handle
    heavy work; this caches the final JSON and ETag to avoid repeat serialization.
    """
    book = (book_param or '').strip().lower()
    book_label = resolve_book_label(book_param)
    title = f"{BOOK_LABEL_TO_NAME.get(book_label, book.title())} {chapter}"
    folder = BOOK_DIR.get(book)
    use_tf = (requested == 'tf') and bhsa_avail
    # Build tree
    tree = None
    if use_tf:
        try:
            tree = parse_chapter_tf_cached(book_label=book_label, chapter=chapter, title=title, include_details=not lite)
        except Exception:
            tree = None
    if tree is None or not isinstance(tree, dict) or not tree.get('children'):
        if folder:
            path = DATA_DIR / folder / f"{chapter:02d}" / f"{folder}{chapter:02d}.CTT"
            if path.exists():
                tree = parse_ctt_cached(path, book_label=book_label, title=title)
            else:
                try:
                    tree = parse_chapter_tf_cached(book_label=book_label, chapter=chapter, title=title, include_details=not lite)
                except Exception:
                    tree = None
        else:
            try:
                tree = parse_chapter_tf_cached(book_label=book_label, chapter=chapter, title=title, include_details=not lite)
            except Exception:
                tree = None
    if tree is None:
        payload = json.dumps({"error": "no data available for this request"}, ensure_ascii=False, separators=(",", ":"))
        etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
        return payload, etag, None
    # lite strip: remove tokens only
    if lite:
        def strip(n):
            if isinstance(n, dict):
                n.pop('tokens', None)
                for c in (n.get('children') or []):
                    strip(c)
        strip(tree)
    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    # Last-Modified based on source data
    last_mod = None
    try:
        src = (tree.get('source') or '').lower()
        if src == 'ctt':
            b = (book_param or '').strip().lower()
            folder2 = BOOK_DIR.get(b)
            ctt_path = None
            if folder2:
                ctt_path = DATA_DIR / folder2 / f"{chapter:02d}" / f"{folder2}{chapter:02d}.CTT"
            last_mod = _latest_ctt_mtime(ctt_path)
        else:
            last_mod = _latest_tf_mtime()
    except Exception:
        last_mod = None
    return payload, etag, last_mod


@lru_cache(maxsize=512)
def _payload_tf_phrases_cached(node_id: int, level: str) -> tuple[str, str]:
    try:
        segs = get_phrase_segments(node_id, level)
    except Exception:
        segs = []
    payload = json.dumps({ 'node_id': node_id, 'level': level, 'segments': segs }, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    return payload, etag


@lru_cache(maxsize=1024)
def _payload_tf_node_cached(node_id: int) -> tuple[str, str]:
    det = {}
    try:
        det = node_details(node_id) or {}
    except Exception:
        det = {}
    if not det:
        payload = json.dumps({"error": "not found"}, ensure_ascii=False, separators=(",", ":"))
        etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
        return payload, etag
    payload = json.dumps(det, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    return payload, etag

@lru_cache(maxsize=64)
def _payload_types_cached(src: str, book: str, max_chapters: int, bhsa_avail: bool) -> tuple[str, str, Optional[str]]:
    if src == 'ctt':
        stats = enumerate_ctt_ctypes()
        types = sorted(({ 'type': k, 'count': v } for k, v in stats.items()), key=lambda x: (-x['count'], x['type']))
        data = { 'source': 'ctt', 'types': types }
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
        last_mod = _latest_ctt_root_mtime(DATA_DIR)
        return payload, etag, last_mod
    # TF path
    if not bhsa_avail:
        payload = json.dumps({ 'error': 'BHSA(Text-Fabric) 데이터가 로컬에 없습니다.' }, ensure_ascii=False, separators=(",", ":"))
        etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
        return payload, etag, _latest_tf_mtime()
    st = typ_stats(book or None, max_chapters=(max_chapters or None))
    types = sorted(({ 'type': k, 'count': v } for k, v in st.items()), key=lambda x: (-x['count'], x['type']))
    data = { 'source': 'tf', 'book': book or None, 'types': types }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    last_mod = _latest_tf_mtime()
    return payload, etag, last_mod


@lru_cache(maxsize=8)
def _payload_gloss_status_cached() -> tuple[str, str, Optional[str]]:
    st = gloss_ko_status()
    payload = json.dumps(st, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    path = st.get('path') if isinstance(st, dict) else None
    lm = None
    try:
        if path:
            p = Path(path)
            if p.exists():
                lm = _httpdate(p.stat().st_mtime)
    except Exception:
        lm = None
    return payload, etag, lm



@app.get("/api/tree")
def api_tree():
    book_param = (request.args.get("book", "genesis") or "").strip()
    book = book_param.lower()
    chapter = int(request.args.get("chapter", "1"))

    # book 파라미터 해석 (라벨/영문명/약칭 모두 허용)
    label = resolve_book_label(book_param)
    if not label:
        return jsonify({"error": f"unsupported book: {book}"}), 400
    book_label = label
    # CTT 폴더는 영문 키 기반으로만 제공(현재 genesis만)
    folder = BOOK_DIR.get(book)
    # 타이틀은 영문 정식 명칭 사용
    title = f"{BOOK_LABEL_TO_NAME.get(book_label, book.title())} {chapter}"

    requested = (request.args.get("source", "tf") or "tf").lower()
    lite = (request.args.get("lite", "1") or "1").lower() not in ("0", "false")
    bhsa_avail = has_local_bhsa_data()
    try:
        payload, etag, last_mod = _tree_payload_cached(book_param, chapter, requested, lite, bhsa_avail)
        inm = request.headers.get('If-None-Match', '')
        if inm and (etag in inm):
            return _resp_304(etag, last_mod)
        return _resp_json(payload, etag, last_mod)
    except Exception:
        return jsonify({"error": "unexpected error"}), 500


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# 폰트 정적 서빙: /font/<파일명>
@app.get("/font/<path:filename>")
def font_files(filename: str):
    return send_from_directory("font", filename)


@app.get("/api/books")
def api_books():
    # 성경 순서(사전 선언 순서) 유지
    items = [{"code": k, "name": v} for k, v in BOOK_LABEL_TO_NAME.items()]
    return jsonify(items)


@app.get("/api/knt/verse")
def api_knt_verse():
    """Return KNT verse text for a given book/chapter/verse.

    Query params:
      book: full English name (e.g., genesis) or label via BOOK_PREFIX
      chapter: integer
      verse: integer
    """
    book = request.args.get("book", "").strip()
    chapter = int(request.args.get("chapter", "0") or 0)
    verse = int(request.args.get("verse", "0") or 0)
    label = resolve_book_label(book)
    if not label or not chapter or not verse:
        return jsonify({"error": "invalid parameters"}), 400
    # Build payload with caching headers (ETag/Last-Modified)
    ko_dir = KNT_LABEL_TO_KO.get(label.upper())
    kpath = (KNT_DIR / ko_dir / f"{chapter:02d}.md") if ko_dir else None
    text = read_knt_verse(label, chapter, verse)
    if text is None:
        return jsonify({"error": "not found"}), 404
    payload = json.dumps({"book_label": label, "chapter": chapter, "verse": verse, "text": text}, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    inm = request.headers.get('If-None-Match', '')
    lm = _latest_ctt_mtime(kpath)
    if inm and (etag in inm):
        return _resp_304(etag, lm)
    return _resp_json(payload, etag, lm)


@app.get("/api/books/chapters")
def api_books_chapters():
    """Return chapter counts per book using KNT Markdown files.

    Response: [{ code: 'GEN', name: 'Genesis', chapters: 50 }, ...]
    """
    items = []
    latest_mtime = 0.0
    for code, name in BOOK_LABEL_TO_NAME.items():
        ko_dir = KNT_LABEL_TO_KO.get(code)
        max_ch = 0
        path = KNT_DIR / ko_dir if ko_dir else None
        if path and path.exists() and path.is_dir():
            try:
                for p in path.iterdir():
                    if not p.is_file():
                        continue
                    fn = p.name
                    if len(fn) >= 5 and fn.endswith('.md'):
                        try:
                            ch = int(fn[:2])
                            if ch > max_ch:
                                max_ch = ch
                        except Exception:
                            pass
                    try:
                        mt = p.stat().st_mtime
                        if mt > latest_mtime:
                            latest_mtime = mt
                    except Exception:
                        pass
            except Exception:
                max_ch = max_ch or 0
        items.append({ 'code': code, 'name': name, 'chapters': int(max_ch) })
    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    inm = request.headers.get('If-None-Match', '')
    last_mod = _httpdate(latest_mtime) if latest_mtime > 0 else _latest_ctt_root_mtime(KNT_DIR)
    if inm and (etag in inm):
        return _resp_304(etag, last_mod)
    return _resp_json(payload, etag, last_mod)


@app.get("/api/tf/phrases")
def api_tf_phrases():
    """선택한 BHSA 노드(clause/clause_atom)에 대한 구(phrase) 분해를 반환.

    Query params:
      node_id: TF node id (int)
      level: phrase | phrase_atom (default: phrase)
    """
    if not has_local_bhsa_data():
        return jsonify({"error": "BHSA(Text-Fabric) 데이터가 로컬에 없습니다."}), 503
    try:
        node_id = int(request.args.get('node_id', '0') or 0)
    except Exception:
        node_id = 0
    level = (request.args.get('level', 'phrase') or 'phrase').strip().lower()
    if not node_id:
        return jsonify({"error": "invalid node_id"}), 400
    key_level = 'phrase' if level != 'phrase_atom' else 'phrase_atom'
    try:
        payload, etag = _payload_tf_phrases_cached(node_id, key_level)
        inm = request.headers.get('If-None-Match', '')
        if inm and (etag in inm):
            return _resp_304(etag)
        return _resp_json(payload, etag)
    except Exception:
        return jsonify({ 'node_id': node_id, 'level': key_level, 'segments': [] })


@app.get("/api/tf/node")
def api_tf_node():
    """선택한 TF 노드(clause/clause_atom)의 상세 정보를 반환 (토큰/글로스/기능 등)."""
    if not has_local_bhsa_data():
        return jsonify({"error": "BHSA(Text-Fabric) 데이터가 로컬에 없습니다."}), 503
    try:
        node_id = int(request.args.get('id', '0') or 0)
    except Exception:
        node_id = 0
    if not node_id:
        return jsonify({"error": "invalid id"}), 400
    try:
        payload, etag = _payload_tf_node_cached(node_id)
        inm = request.headers.get('If-None-Match', '')
        if inm and (etag in inm):
            return _resp_304(etag)
        return _resp_json(payload, etag)
    except Exception:
        return jsonify({"error": "not found"}), 404


@app.get("/api/types")
def api_types():
    """Enumerate clause type codes and counts.

    Query params:
      source: tf|ctt (default tf)
      book: 3-letter label (e.g., GEN) or full name (e.g., Genesis) for TF enumeration; optional
      max_chapters: limit per book for TF enumeration (int)
    """
    src = request.args.get('source', 'tf').lower()
    # normalize TF book code
    book = request.args.get('book', '').strip()
    if book and len(book) > 3:
        rev = { v.lower(): k for k, v in BOOK_LABEL_TO_NAME.items() }
        book = rev.get(book.lower(), '')
    try:
        max_ch = int(request.args.get('max_chapters', '0') or '0')
    except Exception:
        max_ch = 0
    try:
        payload, etag, last_mod = _payload_types_cached(src, book, max_ch, has_local_bhsa_data())
        inm = request.headers.get('If-None-Match', '')
        if inm and (etag in inm):
            return _resp_304(etag, last_mod)
        return _resp_json(payload, etag, last_mod)
    except Exception:
        return jsonify({ 'error': 'types unavailable' }), 500


@app.get("/api/gloss/status")
def api_gloss_status():
    """한글 gloss 매핑 상태 점검."""
    try:
        payload, etag, last_mod = _payload_gloss_status_cached()
        inm = request.headers.get('If-None-Match', '')
        if inm and (etag in inm):
            return _resp_304(etag, last_mod)
        return _resp_json(payload, etag, last_mod)
    except Exception:
        return jsonify(gloss_ko_status())


@app.get("/api/tf/status")
def api_tf_status():
    """TF/BHSA 로컬 데이터 및 gloss 피처 가용성 상태.

    Returns: { has_local_bhsa: bool, has_gloss: bool }
    """
    return jsonify({
        "has_local_bhsa": bool(has_local_bhsa_data()),
        "has_gloss": bool(has_tf_gloss_feature()),
    })


@app.get("/healthz")
def healthz():
    """간단한 헬스 체크 엔드포인트."""
    return jsonify({"status": "ok"})


# Flask 3에서는 before_first_request 훅이 제거되었으므로 별도 예열은 생략합니다.


if __name__ == "__main__":
    # 개발 서버 구동 (환경변수 HOST/PORT 사용, 고정 포트 기본 5001)
    host = os.environ.get("HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "5001"))
    except Exception:
        port = 5001
    # Optionally write chosen port to a file for launchers to detect
    port_file = os.environ.get("PORT_FILE")
    if port_file:
        try:
            with open(port_file, "w") as f:
                f.write(str(port))
        except Exception:
            pass
    debug = os.environ.get("DEBUG", "1") not in ("0", "false", "False")
    app.run(host=host, port=port, debug=debug)
