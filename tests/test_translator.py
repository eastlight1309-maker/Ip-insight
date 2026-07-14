"""엑셀 번역기 엔드투엔드 스모크 테스트 (API 키 없이 데모 모드).

실행: python -m pytest tests/test_translator.py  또는  python tests/test_translator.py
"""

from __future__ import annotations

import io
import os
import sys
import tempfile

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# 로컬 폴백 폴더를 임시 디렉터리로 (실제 저장소를 더럽히지 않도록)
_TMP = tempfile.mkdtemp(prefix="translator_test_")
os.environ.setdefault("LOCAL_TRANSLATOR_INPUT_DIR", os.path.join(_TMP, "in"))
os.environ.setdefault("LOCAL_TRANSLATOR_OUTPUT_DIR", os.path.join(_TMP, "out"))

from exceltranslator import dataiku_io, excel_io, service, translator  # noqa: E402
from exceltranslator.config import settings  # noqa: E402

# load()가 이미 실행됐을 수 있으므로 임시 경로를 강제 반영
settings.local_input_dir = os.environ["LOCAL_TRANSLATOR_INPUT_DIR"]
settings.local_output_dir = os.environ["LOCAL_TRANSLATOR_OUTPUT_DIR"]


def _sample_bytes() -> bytes:
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "product": ["사과", "바나나", ""],
            "desc": ["빨간 과일", "노란 과일", "설명 없음"],
        }
    )
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Sheet1")
    return bio.getvalue()


def test_translate_texts_demo_mode():
    # client=None -> 데모 모드: 비어있지 않은 값에 [EN] 표식
    out = translator.translate_texts(None, ["사과", "", "바나나"], "ko", "en")
    assert out[0].startswith("[EN]")
    assert out[1] == ""  # 빈 값은 그대로
    assert out[2].startswith("[EN]")


def test_full_pipeline_demo_mode():
    out = service.run_translation(
        file_bytes=_sample_bytes(),
        original_filename="sample.xlsx",
        project="테스트 프로젝트",
        columns=["product", "desc"],
        src_code="ko",
        tgt_code="en",
        stamp="testrun",
    )
    # 결과 엑셀은 xlsx(zip) 시그니처
    assert out.xlsx_bytes[:2] == b"PK"
    assert out.output_filename.endswith(".xlsx")
    # 원본 3컬럼 + 번역 2컬럼
    assert len(out.new_columns) == 2
    assert "product [영어]" in out.df.columns
    assert "desc [영어]" in out.df.columns
    # 데모 표식 확인
    assert out.df["product [영어]"].iloc[0].startswith("[EN]")
    assert out.row_count == 3


def test_history_listing():
    # 위 파이프라인 실행 후 프로젝트/파일 목록 조회
    service.run_translation(
        file_bytes=_sample_bytes(),
        original_filename="sample.xlsx",
        project="테스트 프로젝트",
        columns=["product"],
        src_code="auto",
        tgt_code="ja",
        stamp="testrun2",
    )
    projects = dataiku_io.list_projects("output")
    assert any("테스트" in p or "프로젝트" in p for p in projects)

    proj = dataiku_io.safe_project("테스트 프로젝트")
    files = dataiku_io.list_files("output", proj)
    assert any(f.endswith(".xlsx") for f in files)

    # 저장된 파일을 다시 읽어 DataFrame 으로 복원 가능한지
    data = dataiku_io.read_bytes("output", proj, files[0])
    df = excel_io.read_excel(data)
    assert len(df) == 3


if __name__ == "__main__":
    test_translate_texts_demo_mode()
    test_full_pipeline_demo_mode()
    test_history_listing()
    print("모든 번역기 스모크 테스트 통과 ✅")
