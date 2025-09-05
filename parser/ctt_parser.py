from __future__ import annotations
import os
import re
import json
import copy
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List
from .bhsa import verse_text, verse_gloss, map_ascii_tokens_to_bhsa, BOOK_LABEL_TO_NAME, has_local_bhsa_data
from .gloss_ko import gloss_ko_from_english
from .books import BOOK_PREFIX, BOOK_DIR

BOOK_RE = re.compile(r"^[A-Z]{3}\s+\d{2},\d{2}")  # 예: GEN 01,03
LINE_HEAD_RE = re.compile(r"^\s*([A-Z]{3}\s+\d{2},\d{2})\s+([-\w]+)\s+([A-Za-z][\w/]+)")

BRACKET_CONTENT_RE = re.compile(r"\[([^\]]+)\]")  # [ ... ] 덩어리 추출
ANGLE_CONTENTS_RE = re.compile(r"<([^>]+)>")       # <Pr>, <Su> 등 라벨 추출용
ANGLE_RE = re.compile(r"<[^>]+>")                 # <Pr>, <Su> 등 라벨 제거용


def _is_content_line(line: str, book_label: str) -> bool:
    """본문 라인은 선행 공백이 있을 수 있으므로 좌측 공백을 무시하고 검사."""
    return line.lstrip().startswith(book_label)


def _extract_verse_pn_type(line: str) -> Dict[str, str]:
    m = LINE_HEAD_RE.match(line)
    if not m:
        return {"verse": "", "pn": "", "ctype": ""}
    verse, pn, ctype = m.groups()
    return {"verse": verse, "pn": pn, "ctype": ctype}


def _extract_surface_text(line: str) -> str:
    """
    Field 9 안의 [단어 <기능>] 묶음에서 <...> 기능 라벨 제거 후 표면 텍스트만 결합.
    예: [J>MR <Pr>] [>LHJM <Su>] -> "J>MR >LHJM"
    """
    chunks = BRACKET_CONTENT_RE.findall(line)
    words: List[str] = []
    for c in chunks:
        w = ANGLE_RE.sub("", c).strip()
        # 텍스트 유형 표지 등 한 글자 토큰([R], [Q] 등) 제거
        if not w or re.fullmatch(r"[A-Z]", w):
            continue
        words.append(w)
    return " ".join(words)


def _extract_function_labels(line: str) -> List[str]:
    labels: List[str] = []
    for chunk in BRACKET_CONTENT_RE.findall(line):
        labs = ANGLE_CONTENTS_RE.findall(chunk)
        for l in labs:
            # 태그가 복합이면 분해 (예: <sp><Co>)
            for part in re.split(r"[\s/]+", l):
                part = part.strip()
                if part and part not in labels:
                    labels.append(part)
    return labels


# --- ASCII(ETCBC) → 히브리어(자모, 무모음) 단순 변환 ---
_CHAR_MAP = {
    '>': 'א', '<': 'ע',
    'B': 'ב', 'G': 'ג', 'D': 'ד', 'H': 'ה', 'W': 'ו', 'Z': 'ז',
    'X': 'ח', 'V': 'ט', 'J': 'י', 'K': 'כ', 'L': 'ל', 'M': 'מ',
    'N': 'נ', 'S': 'ס', 'P': 'פ', 'Y': 'צ', 'Q': 'ק', 'R': 'ר',
    'C': 'ש', '$': 'ש', 'T': 'ת'
}
_FINAL_MAP = {
    'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פ': 'ף', 'צ': 'ץ'
}


def _translit_token_to_hebrew(token: str) -> str:
    # 접두 하이픈 제거 후 결합, 허용 문자만 유지
    t = re.sub(r"[^A-Za-z<>$-]", "", token)
    t = t.replace('-', '')
    out = ''.join(_CHAR_MAP.get(ch, '') for ch in t)
    if out:
        last = out[-1]
        out = out[:-1] + _FINAL_MAP.get(last, last)
    return out


def _extract_surface_text_hebrew(line: str) -> str:
    """위 표면 텍스트의 각 토큰을 히브리 자모로 변환(무모음)."""
    ascii_surface = _extract_surface_text(line)
    if not ascii_surface:
        return ''
    tokens = ascii_surface.split()
    he = [_translit_token_to_hebrew(tok) for tok in tokens]
    return ' '.join(filter(None, he))


TEXTTYPE_RE = re.compile(r"[NDQ]+")


def _extract_flags_and_texttype(line: str) -> Dict[str, Any]:
    """라인 헤더 영역에서 [Q]/[R] 플래그와 텍스트 타입(N/D/Q)을 추출.
    헤더 영역은 첫 '['(본문 구문 라벨 시작) 이전까지로 간주.
    """
    idx = line.find('[')
    head = line if idx == -1 else line[:idx]
    is_quote = '[Q]' in head
    is_root_mark = '[R]' in head
    # 텍스트 타입: 가장 먼저 발견되는 N/D/Q 연속 토큰을 사용
    tt = None
    m = TEXTTYPE_RE.search(head)
    if m:
        tt = m.group(0)
        # 보수적으로 N/D/Q 중 하나만 색상 기준으로 사용(복합은 Q 우선)
        if 'Q' in tt:
            tt = 'Q'
        elif 'D' in tt:
            tt = 'D'
        elif 'N' in tt:
            tt = 'N'
    return {"is_quote": is_quote, "is_root_mark": is_root_mark, "text_type": tt}


def _depth_by_pipes(line: str) -> int:
    """
    첫 번째 '[' 이전 구간의 '|' 개수를 깊이로 사용.
    """
    idx = line.find('[')
    segment = line if idx == -1 else line[:idx]
    return segment.count('|')


def _parse_verse_ref(verse_field: str) -> Dict[str, int]:
    # 예: "GEN 01,03" -> {chapter:1, verse:3}
    m = re.match(r"^\s*[A-Z]{3}\s+(\d{2}),(\d{2})", verse_field)
    if not m:
        return {"chapter": 0, "verse": 0}
    return {"chapter": int(m.group(1)), "verse": int(m.group(2))}


def parse_ctt(file_path: Path, book_label: str, title: str) -> Dict[str, Any]:
    """
    CTT 파일을 간단 규칙으로 트리 JSON으로 변환.
    각 노드: { id, name, verse, pn, ctype, text, children }
    """
    root = {"id": "root", "name": title, "source": "ctt", "children": []}
    stack: List[Dict[str, Any]] = [root]
    uid = 0

    in_q_block = False
    q_block_id = 0
    q_depth = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            # 인용 블록 경계(=====) 선분 파싱: 토글 방식으로 범위 지정
            if "=====" in line and not _is_content_line(line, book_label):
                if not in_q_block:
                    in_q_block = True
                    q_depth += 1
                    q_block_id += 1
                else:
                    in_q_block = False
                    q_depth = max(0, q_depth - 1)
                continue
            if not _is_content_line(line, book_label):
                continue  # 기타 보조 선(-----) 등 무시
            meta = _extract_verse_pn_type(line)
            surface = _extract_surface_text(line)
            surface_he = _extract_surface_text_hebrew(line)
            flags = _extract_flags_and_texttype(line)
            funclabels = _extract_function_labels(line)
            # BHSA g_word_utf8로 교체 시도(가능한 경우)
            vref = _parse_verse_ref(meta['verse'])
            gloss_text = ''
            gloss_ko_text = ''
            if vref['chapter'] and vref['verse']:
                # 네트워크 환경에서 Text-Fabric 원격 조회로 인한 지연을 피하기 위해
                # 로컬 BHSA 데이터가 있을 때만 매핑을 시도한다.
                if has_local_bhsa_data() and os.environ.get('CTT_SKIP_TF', '0') not in ('1','true','True'):
                    try:
                        # 토큰 단위 매핑 시도
                        he_tokens = surface_he.split() if surface_he else []
                        if he_tokens:
                            mapped = map_ascii_tokens_to_bhsa(book_label, vref['chapter'], vref['verse'], he_tokens)
                            surface_he = " ".join(mapped)
                        else:
                            # 백업: 해당 절 전체 텍스트 사용
                            surface_he = verse_text(book_label, vref['chapter'], vref['verse']) or surface_he
                        # gloss 수집 시도
                        gloss_text = verse_gloss(book_label, vref['chapter'], vref['verse']) or ''
                        # 한글 gloss: 영어 구문 매핑(1열→6열)
                        if gloss_text:
                            gloss_ko_text = gloss_ko_from_english(gloss_text) or ''
                    except Exception:
                        # BHSA가 없거나 실패한 경우, 기존 표면형 유지
                        pass
            depth = _depth_by_pipes(line)  # 0부터 시작

            uid += 1
            # 표시에선 히브리어(BHSA 기반) 표면형을 우선 사용(없을 경우 ASCII 백업)
            display_text = surface_he or surface
            name = f"{meta['verse']} – {meta['ctype']} – {display_text}".strip()
            # 최소 토큰 리스트(형태 정보 없음)
            token_list = []
            if surface_he:
                for tok in surface_he.split():
                    token_list.append({"w": tok, "gloss": ""})

            node = {
                "id": uid,
                "name": name,
                "verse": meta["verse"],
                "pn": meta["pn"],
                "ctype": meta["ctype"],
                "text": surface,
                "text_he": surface_he,
                "text_type": flags.get("text_type"),
                "isQuoteRoot": bool(flags.get("is_quote")),
                "rela": "",  # CTT 기반 간단 파서에서는 미추출
                "funcs": funclabels,
                "tokens": token_list,
                "gloss": gloss_text,
                "gloss_ko": gloss_ko_text,
                "qBlockId": q_block_id if in_q_block else 0,
                "qDepth": q_depth if in_q_block else 0,
                "children": []
            }

            # 스택 조절: stack[0]은 루트이므로, 내용 깊이 0 => 부모는 root
            while len(stack) - 1 > depth:
                stack.pop()
            parent = stack[-1]
            parent["children"].append(node)
            stack.append(node)

    return root


def enumerate_ctt_ctypes(base_dir: Path | None = None) -> Dict[str, int]:
    """Scan local CTT files and count ctype occurrences.

    Looks under data/ctt/<book>/<chapter>/*.CTT by default.
    """
    counts: Dict[str, int] = {}
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[1] / 'data' / 'ctt'
    if not base_dir.exists():
        return counts
    for book_dir in base_dir.iterdir():
        if not book_dir.is_dir():
            continue
        for ch_dir in book_dir.iterdir():
            if not ch_dir.is_dir():
                continue
            for f in ch_dir.glob('*.CTT'):
                try:
                    with f.open('r', encoding='utf-8') as fh:
                        for raw in fh:
                            line = raw.rstrip('\n')
                            if not line.strip():
                                continue
                            m = LINE_HEAD_RE.match(line)
                            if not m:
                                continue
                            # groups: verse, pn, ctype
                            _, _, ctype = m.groups()
                            counts[ctype] = counts.get(ctype, 0) + 1
                except Exception:
                    continue
    return counts


# --- Cached variants for faster repeat loads ---
@lru_cache(maxsize=64)
def _cache_ctt_tree(file_path_str: str, book_label: str, title: str) -> str:
    """Cache CTT parse result as JSON text to ensure immutability across calls."""
    data = parse_ctt(Path(file_path_str), book_label, title)
    return json.dumps(data, ensure_ascii=False)


def parse_ctt_cached(file_path: Path, book_label: str, title: str) -> Dict[str, Any]:
    """Return a fresh copy of a cached CTT parse tree."""
    s = _cache_ctt_tree(str(file_path), book_label, title)
    return json.loads(s)
