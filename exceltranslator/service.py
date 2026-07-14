"""고수준 서비스 계층 — 프론트엔드가 호출하는 단일 진입점.

업로드 -> (Dataiku 입력 폴더 저장) -> 로드 -> 선택 컬럼 번역
-> 결과 컬럼을 맨 뒤에 추가 -> 엑셀 생성 -> (Dataiku 출력 폴더 저장) 흐름을 묶는다.
모든 파일은 프로젝트 이름별 하위 폴더에 저장된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import pandas as pd

from . import dataiku_io, excel_io, llm, translator
from .config import language_label, settings


@dataclass
class RunOutput:
    df: pd.DataFrame                 # 번역 결과가 추가된 DataFrame
    xlsx_bytes: bytes               # 다운로드용 엑셀 바이트
    input_path: str                 # 저장된 입력 파일 경로/식별자
    output_path: str                # 저장된 출력 파일 경로/식별자
    output_filename: str            # 출력 파일명(다운로드 기본 이름)
    project: str = ""
    src_code: str = ""
    tgt_code: str = ""
    translated_columns: List[str] = field(default_factory=list)
    new_columns: List[str] = field(default_factory=list)
    row_count: int = 0
    mode: str = "demo"              # dataiku | openai | demo


def _timestamp_name(prefix: str, ext: str, stamp: str) -> str:
    return f"{prefix}_{stamp}.{ext}"


def _unique_column(existing: List[str], base: str) -> str:
    """중복되지 않는 새 컬럼명 생성."""
    if base not in existing:
        return base
    i = 2
    while f"{base} ({i})" in existing:
        i += 1
    return f"{base} ({i})"


def load_dataframe(file_bytes: bytes, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """엑셀 바이트 -> DataFrame."""
    return excel_io.read_excel(file_bytes, sheet_name)


def run_translation(
    file_bytes: bytes,
    original_filename: str,
    project: str,
    columns: List[str],
    src_code: str,
    tgt_code: str,
    stamp: str,
    sheet_name: Optional[str] = None,
    save_input: bool = True,
    progress: Optional[Callable[[int, int], None]] = None,
) -> RunOutput:
    """전체 번역 파이프라인 실행.

    columns: 번역할 원본 컬럼명 목록.
    각 컬럼의 번역 결과는 '<원본컬럼> [<도착언어>]' 이름으로 맨 뒤에 추가된다.
    """
    # 1) 입력 원본 저장 (Dataiku 입력 폴더 또는 로컬), 프로젝트별 하위 경로
    safe_ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "xlsx"
    input_name = _timestamp_name("input", safe_ext, stamp)
    input_path = ""
    if save_input:
        input_path = dataiku_io.save_bytes("input", project, input_name, file_bytes)

    # 2) 로드
    df = load_dataframe(file_bytes, sheet_name)

    # 3) 번역 클라이언트 준비
    client = llm.get_client()
    mode = client.kind if client is not None else "demo"

    tgt_label = language_label(tgt_code)

    # 4) 컬럼별 번역 -> 맨 뒤에 새 컬럼으로 추가
    #    (여러 컬럼을 번역할 때 전체 진행률을 하나로 합산해서 보고)
    valid_columns = [c for c in columns if c in df.columns]
    per_col_cells = len(df)
    total_cells = per_col_cells * len(valid_columns) if valid_columns else 0
    done_cells = 0

    new_columns: List[str] = []
    for col in valid_columns:
        texts = ["" if pd.isna(v) else str(v) for v in df[col].tolist()]

        def _col_progress(done: int, _total: int, _base=done_cells) -> None:
            if progress and total_cells:
                progress(min(_base + done, total_cells), total_cells)

        translated = translator.translate_texts(
            client, texts, src_code, tgt_code, progress=_col_progress
        )
        done_cells += per_col_cells

        new_col = _unique_column(list(df.columns) + new_columns, f"{col} [{tgt_label}]")
        df[new_col] = translated
        new_columns.append(new_col)

    if progress:
        progress(total_cells, total_cells) if total_cells else progress(1, 1)

    # 5) 결과 엑셀 직렬화
    xlsx_bytes = excel_io.to_excel_bytes(df, sheet_name="translated")

    # 6) 결과 저장 (Dataiku 출력 폴더 또는 로컬), 프로젝트별 하위 경로
    output_filename = _timestamp_name("translated", "xlsx", stamp)
    output_path = dataiku_io.save_bytes("output", project, output_filename, xlsx_bytes)

    return RunOutput(
        df=df,
        xlsx_bytes=xlsx_bytes,
        input_path=input_path,
        output_path=output_path,
        output_filename=output_filename,
        project=project,
        src_code=src_code,
        tgt_code=tgt_code,
        translated_columns=valid_columns,
        new_columns=new_columns,
        row_count=len(df),
        mode=mode,
    )
