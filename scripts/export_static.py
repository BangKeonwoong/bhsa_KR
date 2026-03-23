from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parser.content_service import (
    build_books_chapters_data,
    build_books_data,
    build_capabilities_data,
    build_tree_data,
    build_version_chapter_data,
)
STATIC_FILES = [
    "index.html",
    "styles.css",
    "theme.js",
    "app.js",
    "data-client.js",
    "api-docs.html",
    "openapi.yaml",
]


def _copy_static_assets(dist_dir: Path) -> None:
    static_dir = ROOT / "static"
    font_dir = ROOT / "font"
    for name in STATIC_FILES:
        src = static_dir / name
        if src.exists():
            shutil.copy2(src, dist_dir / name)
    if font_dir.exists():
        shutil.copytree(font_dir, dist_dir / "font", dirs_exist_ok=True)
    (dist_dir / ".nojekyll").write_text("", encoding="utf-8")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _git_sha() -> str:
    env_sha = (os.environ.get("GIT_SHA") or "").strip()
    if env_sha:
        return env_sha
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT))
            .decode("utf-8")
            .strip()
        )
    except Exception:
        return "unknown"


def _chapter_range(chapters: int, max_chapters: int | None) -> range:
    upper = chapters
    if max_chapters is not None:
        upper = min(upper, max_chapters)
    return range(1, max(upper, 0) + 1)


def export_static(out_dir: Path, books_filter: set[str] | None = None, max_chapters: int | None = None) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _copy_static_assets(out_dir)

    data_dir = out_dir / "data"
    books = build_books_data()
    chapter_items = build_books_chapters_data()
    capabilities = build_capabilities_data()

    if books_filter:
        normalized = {value.strip().lower() for value in books_filter if value.strip()}
        books = [book for book in books if str(book.get("book", "")).lower() in normalized]
        chapter_items = [item for item in chapter_items if str(item.get("book", "")).lower() in normalized]

    availability: dict[str, dict[str, dict[str, list[str]]]] = {}
    manifest_books: list[dict] = []

    for item in chapter_items:
        book = str(item["book"])
        chapters = int(item.get("chapters") or 0)
        chapter_availability: dict[str, dict[str, list[str]]] = {}
        book_sources: set[str] = set()
        book_versions: set[str] = set()

        for chapter in _chapter_range(chapters, max_chapters):
            source_hits: list[str] = []
            version_hits: list[str] = []

            for source in ("tf", "ctt"):
                try:
                    lite_tree = build_tree_data(book, chapter, source, True)
                    if lite_tree.get("error") or (lite_tree.get("source") or "").lower() != source:
                        continue
                    full_tree = build_tree_data(book, chapter, source, False)
                    if full_tree.get("error") or (full_tree.get("source") or "").lower() != source:
                        continue
                    _write_json(data_dir / "tree" / source / book / f"{chapter}-lite.json", lite_tree)
                    _write_json(data_dir / "tree" / source / book / f"{chapter}-full.json", full_tree)
                    source_hits.append(source)
                    book_sources.add(source)
                except Exception:
                    continue

            for version in ("knt", "nkrv", "bhs"):
                try:
                    version_data = build_version_chapter_data(version, book, chapter)
                    if not version_data:
                        continue
                    _write_json(data_dir / "versions" / version / book / f"{chapter}.json", version_data)
                    version_hits.append(version)
                    book_versions.add(version)
                except Exception:
                    continue

            if source_hits or version_hits:
                chapter_availability[str(chapter)] = {"tree": sorted(source_hits), "versions": sorted(version_hits)}

        if chapter_availability:
            availability[book] = chapter_availability

        manifest_books.append(
            {
                "book": book,
                "label": item["code"],
                "name": item["name"],
                "chapters": chapters if max_chapters is None else min(chapters, max_chapters),
                "sources": sorted(book_sources),
                "versions": sorted(book_versions),
            }
        )

    manifest = {
        "mode": "static",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git_sha": _git_sha(),
        "capabilities": {
            **capabilities,
            "embedded_node_details": True,
            "embedded_phrase_segments": True,
        },
        "books": manifest_books,
        "availability": availability,
    }

    _write_json(data_dir / "books.json", books)
    _write_json(data_dir / "books-chapters.json", chapter_items)
    _write_json(data_dir / "capabilities.json", capabilities)
    _write_json(data_dir / "manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export bhsa_KR as a static site")
    parser.add_argument("--out", default="dist", help="output directory")
    parser.add_argument("--books", default="", help="comma-separated book values to export")
    parser.add_argument("--max-chapters", type=int, default=None, help="limit chapters per book")
    args = parser.parse_args()

    books_filter = {part.strip() for part in args.books.split(",") if part.strip()} or None
    export_static((ROOT / args.out).resolve(), books_filter=books_filter, max_chapters=args.max_chapters)


if __name__ == "__main__":
    main()
