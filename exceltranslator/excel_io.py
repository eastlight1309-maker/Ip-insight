"""엑셀 파일 로드/저장 유틸리티."""

from __future__ import annotations

import io
from typing import Optional

import pandas as pd


def read_excel(file_bytes: bytes, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """엑셀 바이트를 DataFrame 으로 읽는다 (첫 시트 또는 지정 시트)."""
    bio = io.BytesIO(file_bytes)
    df = pd.read_excel(bio, sheet_name=sheet_name if sheet_name else 0)
    # 혹시 여러 시트를 dict 로 받은 경우 첫 시트만 사용
    if isinstance(df, dict):
        df = next(iter(df.values()))
    return df


def sheet_names(file_bytes: bytes) -> list:
    """엑셀 내 시트 이름 목록."""
    bio = io.BytesIO(file_bytes)
    xls = pd.ExcelFile(bio)
    return list(xls.sheet_names)


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "translated") -> bytes:
    """DataFrame 을 xlsx 바이트로 직렬화."""
    bio = io.BytesIO()
    # 시트명은 엑셀 제한(31자) 준수
    safe_sheet = (sheet_name or "translated")[:31]
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=safe_sheet)
    return bio.getvalue()
