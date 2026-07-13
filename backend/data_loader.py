"""엑셀(특허 + DWPI) 로딩 및 컬럼 정규화.

Derwent DWPI 수출 파일은 컬럼명이 버전/설정에 따라 제각각이라
동의어(synonym)를 정규 컬럼명으로 매핑해 downstream 로직을 단순화한다.
"""

from __future__ import annotations

import io
from typing import Dict, List, Optional

import pandas as pd

# 정규 컬럼명 -> 가능한 원본 컬럼명(소문자, 공백/기호 무시 비교)
CANONICAL_COLUMNS: Dict[str, List[str]] = {
    "publication_number": [
        "publication number", "pub number", "pn", "publication no",
        "patent number", "document number", "공개번호", "특허번호",
    ],
    "title": ["title", "invention title", "제목", "발명의명칭"],
    "abstract": ["abstract", "초록", "요약"],
    "dwpi_title": ["dwpi title", "derwent title", "dwpi 제목"],
    "dwpi_abstract": [
        "dwpi abstract", "derwent abstract", "dwpi novelty", "novelty",
        "dwpi use", "dwpi advantage", "dwpi detailed description",
    ],
    "assignee": [
        "assignee", "assignee/applicant", "applicant", "current assignee",
        "patent assignee", "출원인", "권리자",
    ],
    "dwpi_assignee": ["dwpi assignee", "derwent assignee", "standardized assignee"],
    "inventor": ["inventor", "inventors", "발명자"],
    "priority_date": ["priority date", "earliest priority", "우선일"],
    "application_date": ["application date", "filing date", "출원일"],
    "publication_date": ["publication date", "공개일", "공고일"],
    "ipc": ["ipc", "ipc class", "ipc code", "international patent classification"],
    "cpc": ["cpc", "cpc class", "cpc code"],
    "dwpi_class": ["dwpi class", "dwpi class code", "derwent class", "dwpi class codes"],
    "dwpi_manual_code": ["dwpi manual code", "manual code", "dwpi manual codes"],
    "country": ["country", "publication country", "kind", "국가"],
    "family_id": ["family id", "patent family", "dwpi family", "family"],
    "cited_refs": ["cited references", "cited refs", "backward citations", "references cited"],
    "citing_patents": ["citing patents", "forward citations", "cited by"],
}


# 정규 컬럼명 -> UI 표시용 한글 라벨
CANONICAL_LABELS: Dict[str, str] = {
    "publication_number": "공개/특허 번호",
    "title": "발명의 명칭",
    "abstract": "초록",
    "dwpi_title": "DWPI 제목",
    "dwpi_abstract": "DWPI 초록",
    "assignee": "출원인",
    "dwpi_assignee": "DWPI 표준 출원인",
    "inventor": "발명자",
    "priority_date": "우선일",
    "application_date": "출원일",
    "publication_date": "공개일",
    "ipc": "IPC 분류",
    "cpc": "CPC 분류",
    "dwpi_class": "DWPI Class Code",
    "dwpi_manual_code": "DWPI Manual Code",
    "country": "국가/특허청",
    "family_id": "패밀리 ID",
    "cited_refs": "인용 참조(피인용 대상)",
    "citing_patents": "인용한 특허(피인용)",
}


def label_for(canonical: str) -> str:
    return CANONICAL_LABELS.get(canonical, canonical)


def _norm(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum() or ch == " ").strip()


def _build_reverse_map() -> Dict[str, str]:
    rev: Dict[str, str] = {}
    for canonical, synonyms in CANONICAL_COLUMNS.items():
        for syn in synonyms:
            rev[_norm(syn)] = canonical
    return rev


_REVERSE = _build_reverse_map()


def read_excel(data: bytes, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """바이트 엑셀을 DataFrame으로 읽는다."""
    buf = io.BytesIO(data)
    df = pd.read_excel(buf, sheet_name=sheet_name if sheet_name is not None else 0)
    if isinstance(df, dict):  # sheet_name=None 인 경우 방어
        df = next(iter(df.values()))
    return df


def detect_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """원본 컬럼 -> 정규 컬럼명 자동 매핑 (매칭된 것만)."""
    mapping: Dict[str, str] = {}
    for col in df.columns:
        canonical = _REVERSE.get(_norm(col))
        if canonical and canonical not in mapping.values():
            mapping[col] = canonical
    return mapping


def normalize(df: pd.DataFrame, mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """정규 컬럼명으로 리네이밍한 DataFrame 반환 (원본 컬럼도 유지)."""
    if mapping is None:
        mapping = detect_mapping(df)
    out = df.copy()
    out = out.rename(columns=mapping)
    # 날짜 컬럼 파싱
    for date_col in ("priority_date", "application_date", "publication_date"):
        if date_col in out.columns:
            out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    return out


def available_columns(df: pd.DataFrame) -> List[str]:
    """정규 컬럼 중 실제 존재하는 것."""
    return [c for c in CANONICAL_COLUMNS if c in df.columns]


def invert_selection(selection: Dict[str, Optional[str]]) -> Dict[str, str]:
    """UI용 {정규컬럼: 원본컬럼|None} 을 normalize용 {원본컬럼: 정규컬럼} 으로 변환.

    원본 컬럼이 지정되지 않은(None/빈값) 항목은 제외한다.
    """
    mapping: Dict[str, str] = {}
    for canonical, source in selection.items():
        if source:
            mapping[source] = canonical
    return mapping


def duplicate_sources(selection: Dict[str, Optional[str]]) -> List[str]:
    """하나의 원본 컬럼이 둘 이상의 정규 컬럼에 매핑된 경우(충돌) 목록 반환."""
    used: Dict[str, int] = {}
    for source in selection.values():
        if source:
            used[source] = used.get(source, 0) + 1
    return [src for src, cnt in used.items() if cnt > 1]
