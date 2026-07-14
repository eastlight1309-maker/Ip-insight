"""엔드투엔드 스모크 테스트 (API 키 없이 데모 모드).

실행: python -m pytest tests/  또는  python tests/test_pipeline.py
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from ipinsight import data_loader, service  # noqa: E402
from ipinsight.insights import all_insight_ids  # noqa: E402


def _sample_bytes() -> bytes:
    path = os.path.join(_ROOT, "sample", "sample_dwpi_patents.xlsx")
    with open(path, "rb") as f:
        return f.read()


def test_load_and_normalize():
    df = service.load_dataframe(_sample_bytes())
    cols = data_loader.available_columns(df)
    assert "assignee" in cols
    assert "priority_date" in cols
    assert len(df) > 0


def test_full_pipeline_demo_mode():
    # 로컬 폴백 폴더로 저장되도록 (Dataiku 미설정)
    out = service.run_analysis(
        file_bytes=_sample_bytes(),
        original_filename="sample_dwpi_patents.xlsx",
        insight_ids=all_insight_ids(),
        stamp="testrun",
        save_input=True,
    )
    assert out.ppt_bytes[:2] == b"PK"  # pptx = zip
    assert len(out.results) == len(all_insight_ids())
    assert out.output_path.endswith(".pptx")
    # 각 인사이트 결과에 항목이 채워졌는지 (데모 자리표시자 포함)
    for res in out.results:
        assert res.items, f"{res.insight_id} 항목 비어있음"


if __name__ == "__main__":
    test_load_and_normalize()
    test_full_pipeline_demo_mode()
    print("모든 스모크 테스트 통과 ✅")
