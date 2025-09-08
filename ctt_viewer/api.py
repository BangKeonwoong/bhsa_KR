from __future__ import annotations
from flask import Blueprint, jsonify, request, send_from_directory, current_app
from functools import lru_cache
from pathlib import Path
import os
import json
import hashlib
import re
import time
from typing import Optional

from .http_utils import resp_304, resp_json, APP_START_GMT, httpdate
from .paths import font_dir, ctt_data_dir, knt_dir

from parser.ctt_parser import parse_ctt_cached, enumerate_ctt_ctypes, parse_ctt
from parser.bhsa import (
    parse_chapter_tf_cached,
    parse_chapter_tf,
    typ_stats,
    get_phrase_segments,
    has_local_bhsa_data,
    has_tf_gloss_feature,
    node_details,
)
from parser.books import BOOK_LABEL_TO_NAME, BOOK_DIR, resolve_book_label, KNT_LABEL_TO_KO
from parser.gloss_ko import gloss_ko_status


api_bp = Blueprint("api", __name__)

# LRU 캐시 크기를 환경변수로 조정 가능하게 (모듈 임포트 시 결정)
LRU_TREE_CACHE = int(os.environ.get('LRU_TREE_CACHE', '128'))
LRU_PHRASES_CACHE = int(os.environ.get('LRU_PHRASES_CACHE', '512'))
LRU_NODE_CACHE = int(os.environ.get('LRU_NODE_CACHE', '1024'))
LRU_TYPES_CACHE = int(os.environ.get('LRU_TYPES_CACHE', '64'))
LRU_GLOSS_CACHE = int(os.environ.get('LRU_GLOSS_CACHE', '8'))


def _cache_cfg() -> tuple[int, int]:
    cfg = current_app.config if current_app else {}
    return int(cfg.get('CACHE_MAX_AGE', 300)), int(cfg.get('CACHE_SWR', 60))


def _cache_cfg_tree(is_lite: bool) -> tuple[int, int]:
    cfg = current_app.config if current_app else {}
    if is_lite:
        return int(cfg.get('TREE_LITE_MAX_AGE', 600)), int(cfg.get('TREE_LITE_SWR', 120))
    return int(cfg.get('TREE_FULL_MAX_AGE', 120)), int(cfg.get('TREE_FULL_SWR', 60))


def _is_nocache() -> bool:
    try:
        q = (request.args.get('nocache', '') or '').strip().lower()
        if q in ('1', 'true'): return True
        cc = (request.headers.get('Cache-Control', '') or '').lower()
        if 'no-cache' in cc or 'no-store' in cc: return True
        pragma = (request.headers.get('Pragma', '') or '').lower()
        if 'no-cache' in pragma: return True
        xdbg = (request.headers.get('X-Debug-NoCache', '') or '').strip().lower()
        if xdbg in ('1','true'): return True
    except Exception:
        return False
    return False


def _latest_ctt_mtime(path: Path | None) -> Optional[str]:
    try:
        if path and path.exists():
            return httpdate(path.stat().st_mtime)
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
        return httpdate(latest)
    return None


def _latest_ctt_root_mtime(root: Path | None = None) -> str | None:
    try:
        base = root or ctt_data_dir()
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
            return httpdate(latest)
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
    path = knt_dir() / ko_dir / f"{chapter:02d}.md"
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


def read_knt_chapter(book_label: str, chapter: int) -> Optional[list[dict]]:
    """Read all verses of a chapter from KNT Markdown under KNT/<책>/CC.md.

    Each verse line looks like: '- 3: 텍스트...'
    Returns a list of {verse:int, text:str} or None if file missing.
    """
    ko_dir = KNT_LABEL_TO_KO.get(book_label.upper())
    if not ko_dir:
        return None
    path = knt_dir() / ko_dir / f"{chapter:02d}.md"
    if not path.exists():
        return None
    pat = re.compile(r"^\s*-\s*(\d+)\s*:\s*(.*)$")
    verses: list[dict] = []
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
                verses.append({"verse": v, "text": m.group(2).strip()})
    except Exception:
        return None
    return verses


@lru_cache(maxsize=LRU_TREE_CACHE)
def _tree_payload_cached(book_param: str, chapter: int, requested: str, lite: bool, bhsa_avail: bool, max_depth: int) -> tuple[str, str, Optional[str]]:
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
        data_dir = ctt_data_dir()
        if folder:
            path = data_dir / folder / f"{chapter:02d}" / f"{folder}{chapter:02d}.CTT"
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
    # optional: limit depth (0 keeps only root)
    if isinstance(max_depth, int) and max_depth >= 0:
        def prune(n, d):
            if not isinstance(n, dict):
                return
            if d >= max_depth:
                # cut off children at this level
                if 'children' in n:
                    n['children'] = []
                return
            kids = n.get('children') or []
            for c in kids:
                prune(c, d+1)
        prune(tree, 0)
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
                ctt_path = ctt_data_dir() / folder2 / f"{chapter:02d}" / f"{folder2}{chapter:02d}.CTT"
            last_mod = _latest_ctt_mtime(ctt_path)
        else:
            last_mod = _latest_tf_mtime()
    except Exception:
        last_mod = None
    return payload, etag, last_mod


def _tree_payload_uncached(book_param: str, chapter: int, requested: str, lite: bool, bhsa_avail: bool, max_depth: int) -> tuple[str, str, Optional[str]]:
    book = (book_param or '').strip().lower()
    book_label = resolve_book_label(book_param)
    title = f"{BOOK_LABEL_TO_NAME.get(book_label, book.title())} {chapter}"
    folder = BOOK_DIR.get(book)
    use_tf = (requested == 'tf') and bhsa_avail
    tree = None
    if use_tf:
        try:
            tree = parse_chapter_tf(book_label=book_label, chapter=chapter, title=title, include_details=not lite)
        except Exception:
            tree = None
    if tree is None or not isinstance(tree, dict) or not tree.get('children'):
        data_dir = ctt_data_dir()
        if folder:
            path = data_dir / folder / f"{chapter:02d}" / f"{folder}{chapter:02d}.CTT"
            if path.exists():
                tree = parse_ctt(path, book_label=book_label, title=title)
            else:
                try:
                    tree = parse_chapter_tf(book_label=book_label, chapter=chapter, title=title, include_details=not lite)
                except Exception:
                    tree = None
        else:
            try:
                tree = parse_chapter_tf(book_label=book_label, chapter=chapter, title=title, include_details=not lite)
            except Exception:
                tree = None
    if tree is None:
        payload = json.dumps({"error": "no data available for this request"}, ensure_ascii=False, separators=(",", ":"))
        etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
        return payload, etag, None
    if lite:
        def strip(n):
            if isinstance(n, dict):
                n.pop('tokens', None)
                for c in (n.get('children') or []):
                    strip(c)
        strip(tree)
    if isinstance(max_depth, int) and max_depth >= 0:
        def prune(n, d):
            if not isinstance(n, dict):
                return
            if d >= max_depth:
                if 'children' in n:
                    n['children'] = []
                return
            for c in (n.get('children') or []):
                prune(c, d+1)
        prune(tree, 0)
    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    # Last-Modified similar to cached path
    last_mod = None
    try:
        src = (tree.get('source') or '').lower()
        if src == 'ctt':
            b = (book_param or '').strip().lower()
            folder2 = BOOK_DIR.get(b)
            ctt_path = None
            if folder2:
                ctt_path = ctt_data_dir() / folder2 / f"{chapter:02d}" / f"{folder2}{chapter:02d}.CTT"
            last_mod = _latest_ctt_mtime(ctt_path)
        else:
            last_mod = _latest_tf_mtime()
    except Exception:
        last_mod = None
    return payload, etag, last_mod


@lru_cache(maxsize=LRU_PHRASES_CACHE)
def _payload_tf_phrases_cached(node_id: int, level: str) -> tuple[str, str]:
    try:
        segs = get_phrase_segments(node_id, level)
    except Exception:
        segs = []
    payload = json.dumps({ 'node_id': node_id, 'level': level, 'segments': segs }, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    return payload, etag


@lru_cache(maxsize=LRU_NODE_CACHE)
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


@lru_cache(maxsize=LRU_TYPES_CACHE)
def _payload_types_cached(src: str, book: str, max_chapters: int, bhsa_avail: bool) -> tuple[str, str, Optional[str]]:
    if src == 'ctt':
        stats = enumerate_ctt_ctypes()
        types = sorted(({ 'type': k, 'count': v } for k, v in stats.items()), key=lambda x: (-x['count'], x['type']))
        data = { 'source': 'ctt', 'types': types }
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
        last_mod = _latest_ctt_root_mtime(ctt_data_dir())
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


@lru_cache(maxsize=LRU_GLOSS_CACHE)
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
                lm = httpdate(p.stat().st_mtime)
    except Exception:
        lm = None
    return payload, etag, lm


@api_bp.get("/api/tree")
def api_tree():
    book_param = (request.args.get("book", "genesis") or "").strip()
    book = book_param.lower()
    chapter = int(request.args.get("chapter", "1"))

    label = resolve_book_label(book_param)
    if not label:
        return jsonify({"error": f"unsupported book: {book}"}), 400

    requested = (request.args.get("source", "tf") or "tf").lower()
    lite = (request.args.get("lite", "1") or "1").lower() not in ("0", "false")
    try:
        max_depth = request.args.get('max_depth')
        max_depth = int(max_depth) if (max_depth is not None and str(max_depth).strip() != '') else -1
        if max_depth < 0:
            max_depth = -1
    except Exception:
        max_depth = -1
    bhsa_avail = has_local_bhsa_data()
    try:
        nocache = _is_nocache()
        if nocache:
            payload, etag, last_mod = _tree_payload_uncached(book_param, chapter, requested, lite, bhsa_avail, max_depth)
            # force fresh response
            return resp_json(payload, etag, last_mod, 0, 0)
        payload, etag, last_mod = _tree_payload_cached(book_param, chapter, requested, lite, bhsa_avail, max_depth)
        inm = request.headers.get('If-None-Match', '')
        ma, swr = _cache_cfg_tree(lite)
        if inm and (etag in inm):
            return resp_304(etag, last_mod, ma, swr)
        return resp_json(payload, etag, last_mod, ma, swr)
    except Exception:
        return jsonify({"error": "unexpected error"}), 500


@api_bp.get("/api/books")
def api_books():
    items = [{"code": k, "name": v} for k, v in BOOK_LABEL_TO_NAME.items()]
    return jsonify(items)


@api_bp.get("/api/knt/verse")
def api_knt_verse():
    book = request.args.get("book", "").strip()
    chapter = int(request.args.get("chapter", "0") or 0)
    verse = int(request.args.get("verse", "0") or 0)
    label = resolve_book_label(book)
    if not label or not chapter or not verse:
        return jsonify({"error": "invalid parameters"}), 400
    ko_dir = KNT_LABEL_TO_KO.get(label.upper())
    kpath = (knt_dir() / ko_dir / f"{chapter:02d}.md") if ko_dir else None
    text = read_knt_verse(label, chapter, verse)
    if text is None:
        return jsonify({"error": "not found"}), 404
    payload = json.dumps({"book_label": label, "chapter": chapter, "verse": verse, "text": text}, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    inm = request.headers.get('If-None-Match', '')
    lm = _latest_ctt_mtime(kpath)
    if _is_nocache():
        return resp_json(payload, etag, lm, 0, 0)
    ma, swr = _cache_cfg()
    if inm and (etag in inm):
        return resp_304(etag, lm, ma, swr)
    return resp_json(payload, etag, lm, ma, swr)


@api_bp.get("/api/knt/chapter")
def api_knt_chapter():
    book = request.args.get("book", "").strip()
    try:
        chapter = int(request.args.get("chapter", "0") or 0)
    except Exception:
        chapter = 0
    label = resolve_book_label(book)
    if not label or not chapter:
        return jsonify({"error": "invalid parameters"}), 400
    ko_dir = KNT_LABEL_TO_KO.get(label.upper())
    kpath = (knt_dir() / ko_dir / f"{chapter:02d}.md") if ko_dir else None
    data = read_knt_chapter(label, chapter)
    if data is None:
        return jsonify({"error": "not found"}), 404
    payload = json.dumps({"book_label": label, "chapter": chapter, "verses": data}, ensure_ascii=False, separators=(",", ":"))
    etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
    inm = request.headers.get('If-None-Match', '')
    lm = _latest_ctt_mtime(kpath)
    if _is_nocache():
        return resp_json(payload, etag, lm, 0, 0)
    ma, swr = _cache_cfg()
    if inm and (etag in inm):
        return resp_304(etag, lm, ma, swr)
    return resp_json(payload, etag, lm, ma, swr)


@api_bp.get("/api/books/chapters")
def api_books_chapters():
    items = []
    latest_mtime = 0.0
    KNT_DIR = knt_dir()
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
    last_mod = httpdate(latest_mtime) if latest_mtime > 0 else _latest_ctt_root_mtime(KNT_DIR)
    if _is_nocache():
        return resp_json(payload, etag, last_mod, 0, 0)
    ma, swr = _cache_cfg()
    if inm and (etag in inm):
        return resp_304(etag, last_mod, ma, swr)
    return resp_json(payload, etag, last_mod, ma, swr)


@api_bp.get("/api/tf/phrases")
def api_tf_phrases():
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
        if _is_nocache():
            segs = get_phrase_segments(node_id, key_level)
            payload = json.dumps({ 'node_id': node_id, 'level': key_level, 'segments': segs }, ensure_ascii=False, separators=(",", ":"))
            etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
            return resp_json(payload, etag, None, 0, 0)
        payload, etag = _payload_tf_phrases_cached(node_id, key_level)
        inm = request.headers.get('If-None-Match', '')
        ma, swr = _cache_cfg()
        if inm and (etag in inm):
            return resp_304(etag, None, ma, swr)
        return resp_json(payload, etag, None, ma, swr)
    except Exception:
        return jsonify({ 'node_id': node_id, 'level': key_level, 'segments': [] })


@api_bp.get("/api/tf/node")
def api_tf_node():
    if not has_local_bhsa_data():
        return jsonify({"error": "BHSA(Text-Fabric) 데이터가 로컬에 없습니다."}), 503
    try:
        node_id = int(request.args.get('id', '0') or 0)
    except Exception:
        node_id = 0
    if not node_id:
        return jsonify({"error": "invalid id"}), 400
    try:
        if _is_nocache():
            det = node_details(node_id) or {}
            if not det:
                return jsonify({"error": "not found"}), 404
            payload = json.dumps(det, ensure_ascii=False, separators=(",", ":"))
            etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
            return resp_json(payload, etag, None, 0, 0)
        payload, etag = _payload_tf_node_cached(node_id)
        inm = request.headers.get('If-None-Match', '')
        ma, swr = _cache_cfg()
        if inm and (etag in inm):
            return resp_304(etag, None, ma, swr)
        return resp_json(payload, etag, None, ma, swr)
    except Exception:
        return jsonify({"error": "not found"}), 404


@api_bp.get("/api/types")
def api_types():
    src = request.args.get('source', 'tf').lower()
    book = request.args.get('book', '').strip()
    if book and len(book) > 3:
        rev = { v.lower(): k for k, v in BOOK_LABEL_TO_NAME.items() }
        book = rev.get(book.lower(), '')
    try:
        max_ch = int(request.args.get('max_chapters', '0') or '0')
    except Exception:
        max_ch = 0
    try:
        if _is_nocache():
            if src == 'ctt':
                stats = enumerate_ctt_ctypes()
                types = sorted(({ 'type': k, 'count': v } for k, v in stats.items()), key=lambda x: (-x['count'], x['type']))
                data = { 'source': 'ctt', 'types': types }
                payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
                etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
                return resp_json(payload, etag, _latest_ctt_root_mtime(ctt_data_dir()), 0, 0)
            if not has_local_bhsa_data():
                payload = json.dumps({ 'error': 'BHSA(Text-Fabric) 데이터가 로컬에 없습니다.' }, ensure_ascii=False, separators=(",", ":"))
                etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
                return resp_json(payload, etag, _latest_tf_mtime(), 0, 0)
            st = typ_stats(book or None, max_chapters=(max_ch or None))
            types = sorted(({ 'type': k, 'count': v } for k, v in st.items()), key=lambda x: (-x['count'], x['type']))
            data = { 'source': 'tf', 'book': book or None, 'types': types }
            payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
            return resp_json(payload, etag, _latest_tf_mtime(), 0, 0)
        payload, etag, last_mod = _payload_types_cached(src, book, max_ch, has_local_bhsa_data())
        inm = request.headers.get('If-None-Match', '')
        ma, swr = _cache_cfg()
        if inm and (etag in inm):
            return resp_304(etag, last_mod, ma, swr)
        return resp_json(payload, etag, last_mod, ma, swr)
    except Exception:
        return jsonify({ 'error': 'types unavailable' }), 500


@api_bp.get("/api/gloss/status")
def api_gloss_status():
    try:
        if _is_nocache():
            st = gloss_ko_status()
            payload = json.dumps(st, ensure_ascii=False, separators=(",", ":"))
            etag = hashlib.md5(payload.encode('utf-8')).hexdigest()
            last_mod = None
            try:
                p = Path(st.get('path') or '') if isinstance(st, dict) else None
                if p and p.exists(): last_mod = httpdate(p.stat().st_mtime)
            except Exception:
                last_mod = None
            return resp_json(payload, etag, last_mod, 0, 0)
        payload, etag, last_mod = _payload_gloss_status_cached()
        inm = request.headers.get('If-None-Match', '')
        ma, swr = _cache_cfg()
        if inm and (etag in inm):
            return resp_304(etag, last_mod, ma, swr)
        return resp_json(payload, etag, last_mod, ma, swr)
    except Exception:
        return jsonify(gloss_ko_status())


@api_bp.get("/api/tf/status")
def api_tf_status():
    return jsonify({
        "has_local_bhsa": bool(has_local_bhsa_data()),
        "has_gloss": bool(has_tf_gloss_feature()),
    })


def register_misc_routes(app, root: Path) -> None:
    # index and font routes not in API blueprint
    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/font/<path:filename>")
    def font_files(filename: str):
        return send_from_directory(str(font_dir()), filename)

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    @app.get("/api/version")
    def api_version():
        """간단한 빌드/버전 정보.

        우선순위: 환경변수 APP_VERSION, GIT_SHA → git rev-parse → unknown
        """
        ver = os.environ.get('APP_VERSION') or ''
        sha = os.environ.get('GIT_SHA') or ''
        if not sha:
            # best-effort 로컬 git 해시 조회
            try:
                import subprocess
                sha = (subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(root))).decode().strip()
            except Exception:
                sha = ''
        if not ver:
            ver = sha or 'unknown'
        return jsonify({ 'version': ver, 'git_sha': sha or 'unknown' })

    @app.get("/api/docs")
    def api_docs():
        return app.send_static_file("api-docs.html")
