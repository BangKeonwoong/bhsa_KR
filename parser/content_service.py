from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ctt_viewer.paths import ctt_data_dir

from .bhsa import (
    get_tf_status,
    get_phrase_segments,
    has_local_bhsa_data,
    has_tf_gloss_feature,
    parse_chapter_tf,
    parse_chapter_tf_cached,
)
from .books import BOOK_DIR, BOOK_LABEL_TO_NAME, resolve_book_label
from .ctt_parser import parse_ctt, parse_ctt_cached
from .gloss_ko import gloss_ko_status
from .versions_io import read_bhs_chapter, read_knt_chapter, read_nkrv_chapter, get_knt_max_chapter


def book_value_for_label(book_label: str) -> str:
    name = BOOK_LABEL_TO_NAME.get((book_label or "").upper(), book_label or "")
    return name.lower()


def build_books_data() -> list[dict]:
    items: list[dict] = []
    for code, name in BOOK_LABEL_TO_NAME.items():
        items.append({"book": book_value_for_label(code), "code": code, "name": name})
    return items


def build_books_chapters_data() -> list[dict]:
    items: list[dict] = []
    for book in build_books_data():
        code = str(book["code"])
        items.append(
            {
                "book": book["book"],
                "code": code,
                "name": book["name"],
                "chapters": int(get_knt_max_chapter(code)),
            }
        )
    return items


def build_capabilities_data(*, start_warmup: bool = False, require_details: bool = False) -> dict:
    gloss_status = gloss_ko_status()
    status = get_tf_status(start_warmup=start_warmup, require_details=require_details)
    status["has_local_bhsa"] = bool(status.get("has_local_bhsa", has_local_bhsa_data()))
    status["has_gloss"] = bool(status.get("has_gloss", has_tf_gloss_feature()))
    status["has_gloss_ko_csv"] = bool(gloss_status.get("ok"))
    return status


def _tree_has_children(tree: Any) -> bool:
    return isinstance(tree, dict) and bool(tree.get("children"))


def _ctt_path(book_param: str, chapter: int) -> Optional[Path]:
    folder = BOOK_DIR.get((book_param or "").strip().lower())
    if not folder:
        return None
    path = ctt_data_dir() / folder / f"{int(chapter):02d}" / f"{folder}{int(chapter):02d}.CTT"
    return path if path.exists() else None


def _load_tree_from_source(
    source: str,
    *,
    book_param: str,
    book_label: str,
    chapter: int,
    title: str,
    include_details: bool,
    use_cache: bool,
) -> Optional[dict]:
    if source == "tf":
        if not has_local_bhsa_data():
            return None
        parser = parse_chapter_tf_cached if use_cache else parse_chapter_tf
        return parser(book_label=book_label, chapter=chapter, title=title, include_details=include_details)
    if source == "ctt":
        path = _ctt_path(book_param, chapter)
        if not path:
            return None
        parser = parse_ctt_cached if use_cache else parse_ctt
        return parser(path, book_label=book_label, title=title)
    return None


def _attach_phrase_segments(tree: dict) -> None:
    def walk(node: dict) -> None:
        node_id = node.get("id")
        if isinstance(node_id, int):
            try:
                segments = get_phrase_segments(node_id, "phrase")
            except Exception:
                segments = []
            if segments:
                node["phrase_segments"] = segments
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    walk(tree)


def _strip_lite_fields(tree: dict) -> None:
    def walk(node: dict) -> None:
        node.pop("tokens", None)
        node.pop("phrase_segments", None)
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    walk(tree)


def _prune_depth(tree: dict, max_depth: int) -> None:
    if not isinstance(max_depth, int) or max_depth < 0:
        return

    def walk(node: dict, depth: int) -> None:
        if depth >= max_depth:
            node["children"] = []
            return
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child, depth + 1)

    walk(tree, 0)


def build_tree_data(
    book: str,
    chapter: int,
    requested_source: str,
    lite: bool,
    max_depth: int = -1,
    *,
    use_cache: bool = True,
) -> dict:
    book_param = (book or "").strip()
    book_label = resolve_book_label(book_param)
    if not book_label:
        return {"error": "invalid book"}
    chapter_num = int(chapter)
    requested = (requested_source or "").strip().lower()
    title = f"{BOOK_LABEL_TO_NAME.get(book_label, book_param.title())} {chapter_num}"
    candidates: list[str]
    if requested == "tf":
        candidates = ["tf", "ctt"]
    elif requested == "ctt":
        candidates = ["ctt", "tf"]
    else:
        candidates = ["tf", "ctt"] if has_local_bhsa_data() else ["ctt", "tf"]

    tree: Optional[dict] = None
    for source in candidates:
        tree = _load_tree_from_source(
            source,
            book_param=book_param,
            book_label=book_label,
            chapter=chapter_num,
            title=title,
            include_details=not lite,
            use_cache=use_cache,
        )
        if _tree_has_children(tree):
            break
    if not _tree_has_children(tree):
        return {"error": "no data available for this request"}

    assert tree is not None
    if not lite and (tree.get("source") or "").lower() == "tf":
        _attach_phrase_segments(tree)
    if lite:
        _strip_lite_fields(tree)
    _prune_depth(tree, max_depth)
    return tree


def build_version_chapter_data(version: str, book: str, chapter: int) -> Optional[dict]:
    book_label = resolve_book_label(book)
    if not book_label:
        return None
    version_key = (version or "").strip().lower()
    chapter_num = int(chapter)
    if version_key == "knt":
        verses = read_knt_chapter(book_label, chapter_num)
    elif version_key == "nkrv":
        verses = read_nkrv_chapter(book_label, chapter_num)
    elif version_key == "bhs":
        verses = read_bhs_chapter(book_label, chapter_num)
    else:
        return None
    if verses is None:
        return None
    return {"version": version_key, "book_label": book_label, "chapter": chapter_num, "verses": verses}
