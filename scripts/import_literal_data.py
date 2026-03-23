from __future__ import annotations

import argparse
import csv
import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CSV_BOOK_OVERRIDES = {
    "Song of Solomon": "Song of Songs",
}


def _canonical_book_name(raw: str) -> str:
    book = (raw or "").strip()
    return CSV_BOOK_OVERRIDES.get(book, book)


def _parse_int(value: str) -> int | None:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed


def build_literal_index(csv_path: Path) -> dict:
    books: OrderedDict[str, OrderedDict[str, OrderedDict[str, list[dict]]]] = OrderedDict()
    aliases: dict[str, str] = {}
    row_count = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if not reader.fieldnames:
            raise ValueError(f"Missing header row in {csv_path}")
        for row in reader:
            row_count += 1
            book = _canonical_book_name(row.get("Book", ""))
            chapter = _parse_int(row.get("Chapter", ""))
            verse = _parse_int(row.get("Verse", ""))
            if not book or chapter is None or verse is None:
                continue

            clause = {
                "clauseType": (row.get("Clause Type") or "").strip(),
                "motherClauseType": (row.get("Mother Clause Type") or "").strip(),
                "predictedTAM": (row.get("Predicted TAM") or "").strip(),
                "hebrewText": (row.get("Hebrew Text") or "").strip(),
                "wordOrder": (row.get("Word Order") or "").strip(),
                "koreanLiteral": (row.get("Korean Literal") or "").strip(),
            }
            if not clause["koreanLiteral"]:
                continue

            books.setdefault(book, OrderedDict())
            aliases.setdefault(book.lower(), book)
            aliases.setdefault(book.replace(" ", "_").lower(), book)
            chapter_map = books[book].setdefault(str(chapter), OrderedDict())
            verse_list = chapter_map.setdefault(str(verse), [])
            verse_list.append(clause)

    return {
        "meta": {
            "source": str(csv_path.name),
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "row_count": row_count,
            "book_count": len(books),
        },
        "aliases": aliases,
        "books": books,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the bible-viewer CSV into static/literal-index.json")
    parser.add_argument(
        "--csv",
        default=str(Path("/tmp/bible-viewer-inspect/성경 직역 정보 2.csv")),
        help="source CSV path",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "static" / "literal-index.json"),
        help="output JSON path",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    index = build_literal_index(csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
