from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional

from ctt_viewer.paths import bhs_dir, knt_dir, nkrv_dir

from .books import BOOK_LABEL_TO_NAME, KNT_LABEL_TO_KO


def _nfc(text: str | None) -> str:
    try:
        return unicodedata.normalize("NFC", text or "")
    except Exception:
        return text or ""


def find_knt_chapter_path(book_label: str, chapter: int) -> Optional[Path]:
    ko_dir = KNT_LABEL_TO_KO.get((book_label or "").upper())
    if not ko_dir:
        return None
    path = knt_dir() / ko_dir / f"{int(chapter):02d}.md"
    return path if path.exists() else None


def read_knt_verse(book_label: str, chapter: int, verse: int) -> Optional[str]:
    path = find_knt_chapter_path(book_label, chapter)
    if path is None:
        return None
    pattern = re.compile(r"^\s*-\s*(\d+)\s*:\s*(.*)$")
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                match = pattern.match(line)
                if not match:
                    continue
                try:
                    number = int(match.group(1))
                except Exception:
                    continue
                if number == int(verse):
                    return match.group(2).strip()
    except Exception:
        return None
    return None


def read_knt_chapter(book_label: str, chapter: int) -> Optional[list[dict]]:
    path = find_knt_chapter_path(book_label, chapter)
    if path is None:
        return None
    pattern = re.compile(r"^\s*-\s*(\d+)\s*:\s*(.*)$")
    verses: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                match = pattern.match(line)
                if not match:
                    continue
                try:
                    number = int(match.group(1))
                except Exception:
                    continue
                verses.append({"verse": number, "text": match.group(2).strip()})
    except Exception:
        return None
    return verses


def get_knt_max_chapter(book_label: str) -> int:
    ko_dir = KNT_LABEL_TO_KO.get((book_label or "").upper())
    if not ko_dir:
        return 0
    path = knt_dir() / ko_dir
    if not path.exists() or not path.is_dir():
        return 0
    max_chapter = 0
    try:
        for child in path.iterdir():
            if not child.is_file() or not child.name.endswith(".md"):
                continue
            try:
                chapter = int(child.stem)
            except Exception:
                continue
            max_chapter = max(max_chapter, chapter)
    except Exception:
        return max_chapter
    return max_chapter


def find_nkrv_book_dir(book_label: str) -> Optional[Path]:
    try:
        root = nkrv_dir()
        if not root.exists():
            return None
        ko_name = _nfc(KNT_LABEL_TO_KO.get((book_label or "").upper()))
        if not ko_name:
            return None
        for child in root.iterdir():
            if not child.is_dir():
                continue
            folder_name = _nfc(child.name)
            base_name = folder_name.split("-", 1)[-1] if "-" in folder_name else folder_name
            if _nfc(base_name) == ko_name:
                return child
    except Exception:
        return None
    return None


def find_nkrv_chapter_path(book_label: str, chapter: int) -> Optional[Path]:
    book_dir = find_nkrv_book_dir(book_label)
    if not book_dir:
        return None
    path = book_dir / f"{int(chapter):03d}.md"
    return path if path.exists() else None


def read_nkrv_chapter(book_label: str, chapter: int) -> Optional[list[dict]]:
    path = find_nkrv_chapter_path(book_label, chapter)
    if path is None:
        return None
    verses: list[dict] = []
    pattern = re.compile(r"^\s*(\d+)\s*\.\s*(.+)$")
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                match = pattern.match(line)
                if not match:
                    continue
                try:
                    number = int(match.group(1))
                except Exception:
                    continue
                verses.append({"verse": number, "text": match.group(2).strip()})
    except Exception:
        return None
    return verses


def find_bhs_book_dir(book_label: str) -> Optional[Path]:
    try:
        root = bhs_dir()
        if not root.exists():
            return None
        english_name = BOOK_LABEL_TO_NAME.get((book_label or "").upper())
        if not english_name:
            return None
        suffix = english_name.lower()
        for child in root.iterdir():
            if child.is_dir() and child.name.lower().endswith(suffix):
                return child
    except Exception:
        return None
    return None


def find_bhs_chapter_path(book_label: str, chapter: int) -> Optional[Path]:
    book_dir = find_bhs_book_dir(book_label)
    if not book_dir:
        return None
    path = book_dir / f"{int(chapter):02d}.md"
    return path if path.exists() else None


def read_bhs_chapter(book_label: str, chapter: int) -> Optional[list[dict]]:
    path = find_bhs_chapter_path(book_label, chapter)
    if path is None:
        return None
    verses: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        index = 0
        if index < len(lines) and lines[index].strip() == "---":
            index += 1
            while index < len(lines) and lines[index].strip() != "---":
                index += 1
            if index < len(lines) and lines[index].strip() == "---":
                index += 1
        pattern = re.compile(r"^\s*(\d+)\s+(.+)$")
        for line in lines[index:]:
            match = pattern.match(line)
            if not match:
                continue
            try:
                number = int(match.group(1))
            except Exception:
                continue
            verses.append({"verse": number, "text": match.group(2).strip()})
    except Exception:
        return None
    return verses
