from __future__ import annotations
from typing import Dict, Optional

# Canonical BHSA 3-letter label → English book name
BOOK_LABEL_TO_NAME: Dict[str, str] = {
    "GEN": "Genesis",
    "EXO": "Exodus",
    "LEV": "Leviticus",
    "NUM": "Numbers",
    "DEU": "Deuteronomy",
    "JOS": "Joshua",
    "JDG": "Judges",
    "RUT": "Ruth",
    "1SA": "1 Samuel",
    "2SA": "2 Samuel",
    "1KI": "1 Kings",
    "2KI": "2 Kings",
    "1CH": "1 Chronicles",
    "2CH": "2 Chronicles",
    "EZR": "Ezra",
    "NEH": "Nehemiah",
    "EST": "Esther",
    "JOB": "Job",
    "PSA": "Psalms",
    "PRO": "Proverbs",
    "ECC": "Ecclesiastes",
    "SOS": "Song of Songs",
    "ISA": "Isaiah",
    "JER": "Jeremiah",
    "LAM": "Lamentations",
    "EZE": "Ezekiel",
    "DAN": "Daniel",
    "HOS": "Hosea",
    "JOL": "Joel",
    "AMO": "Amos",
    "OBA": "Obadiah",
    "JON": "Jonah",
    "MIC": "Micah",
    "NAH": "Nahum",
    "HAB": "Habakkuk",
    "ZEP": "Zephaniah",
    "HAG": "Haggai",
    "ZEC": "Zechariah",
    "MAL": "Malachi",
}

# Short, lowercased keys accepted by the app → 3-letter label
# Keep minimal set for local CTT data support; TF side can resolve via full names.
BOOK_PREFIX: Dict[str, str] = {
    "genesis": "GEN",
}

# Local CTT folder mapping (lowercased English name → directory name)
BOOK_DIR: Dict[str, str] = {
    "genesis": "genesis",
}

# BHSA label → Korean book folder name (for KNT lookup)
KNT_LABEL_TO_KO: Dict[str, str] = {
    "GEN": "창세기",
    "EXO": "출애굽기",
    "LEV": "레위기",
    "NUM": "민수기",
    "DEU": "신명기",
    "JOS": "여호수아",
    "JDG": "사사기",
    "RUT": "룻기",
    "1SA": "사무엘상",
    "2SA": "사무엘하",
    "1KI": "열왕기상",
    "2KI": "열왕기하",
    "1CH": "역대상",
    "2CH": "역대하",
    "EZR": "에스라",
    "NEH": "느헤미야",
    "EST": "에스더",
    "JOB": "욥기",
    "PSA": "시편",
    "PRO": "잠언",
    "ECC": "전도서",
    "SOS": "아가",
    "ISA": "이사야",
    "JER": "예레미야",
    "LAM": "예레미야애가",
    "EZE": "에스겔",
    "DAN": "다니엘",
    "HOS": "호세아",
    "JOL": "요엘",
    "AMO": "아모스",
    "OBA": "오바댜",
    "JON": "요나",
    "MIC": "미가",
    "NAH": "나훔",
    "HAB": "하박국",
    "ZEP": "스바냐",
    "HAG": "학개",
    "ZEC": "스가랴",
    "MAL": "말라기",
}


def resolve_book_label(book: str) -> Optional[str]:
    """Resolve request 'book' param to 3-letter BHSA label.

    Accepts:
    - direct 3-letter label (e.g., 'GEN', '1SA')
    - lowercased keys in BOOK_PREFIX (e.g., 'genesis')
    - full English names from BOOK_LABEL_TO_NAME (e.g., 'Genesis')
    Returns None if not resolvable.
    """
    if not book:
        return None
    raw = (book or "").strip()
    low = raw.lower()
    up = raw.upper()
    if up in BOOK_LABEL_TO_NAME:
        return up
    if low in BOOK_PREFIX:
        return BOOK_PREFIX[low]
    # reverse map of full English names (case-insensitive)
    rev = {v.lower(): k for k, v in BOOK_LABEL_TO_NAME.items()}
    return rev.get(low)

