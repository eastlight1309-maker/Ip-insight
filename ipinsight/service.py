"""고수준 서비스 계층 — 프론트엔드가 호출하는 단일 진입점.

업로드 -> (Dataiku 입력 폴더 저장) -> 로드/정규화 -> LLM 분석
-> PPT 생성 -> (Dataiku 출력 폴더 저장) 흐름을 묶는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from . import analytics, data_loader, dataiku_io, ppt_builder
from .llm_analyzer import InsightResult, analyze


@dataclass
class RunOutput:
    df: pd.DataFrame
    results: List[InsightResult]
    ppt_bytes: bytes
    input_path: str
    output_path: str
    overview: Dict[str, object] = field(default_factory=dict)


def _timestamp_name(prefix: str, ext: str, stamp: str) -> str:
    return f"{prefix}_{stamp}.{ext}"


def load_dataframe(file_bytes: bytes, mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """엑셀 바이트 -> 정규화된 DataFrame."""
    raw = data_loader.read_excel(file_bytes)
    return data_loader.normalize(raw, mapping)


def run_analysis(
    file_bytes: bytes,
    original_filename: str,
    insight_ids: List[str],
    stamp: str,
    mapping: Optional[Dict[str, str]] = None,
    save_input: bool = True,
) -> RunOutput:
    """전체 파이프라인 실행.

    stamp: 파일명에 쓸 타임스탬프 문자열(호출측에서 생성 — 재현성/테스트 용이).
    """
    # 1) 입력 원본 저장 (Dataiku 입력 폴더 또는 로컬)
    safe_ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "xlsx"
    input_name = _timestamp_name("input_patents", safe_ext, stamp)
    input_path = ""
    if save_input:
        input_path = dataiku_io.save_bytes("input", input_name, file_bytes)

    # 2) 로드 & 정규화
    df = load_dataframe(file_bytes, mapping)
    overview = analytics.overview(df)

    # 3) LLM 분석
    results = analyze(insight_ids, df)

    # 4) PPT 생성
    ppt_bytes = ppt_builder.build_ppt(results, overview=overview)

    # 5) 결과 PPT 저장 (Dataiku 출력 폴더 또는 로컬)
    output_name = _timestamp_name("ip_insight_report", "pptx", stamp)
    output_path = dataiku_io.save_bytes("output", output_name, ppt_bytes)

    return RunOutput(
        df=df,
        results=results,
        ppt_bytes=ppt_bytes,
        input_path=input_path,
        output_path=output_path,
        overview=overview,
    )
