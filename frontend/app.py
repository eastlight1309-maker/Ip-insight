"""IP Insight — Streamlit 프론트엔드.

Dataiku 의 Streamlit 웹앱으로 배포하는 것을 전제로 한다.
백엔드 로직은 `backend` 패키지에 분리되어 있고, 이 파일은 UI만 담당한다.

실행(로컬):  streamlit run frontend/app.py
Dataiku:     웹앱 코드로 본 파일 내용을 사용 (아래 sys.path 처리로 backend import).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

# 프로젝트 루트를 import 경로에 추가 (Dataiku 웹앱/로컬 모두 대응)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from backend import data_loader, dataiku_io, llm, service  # noqa: E402
from backend.config import ALLOWED_LLM_CANDIDATES, settings  # noqa: E402
from backend.insights import INSIGHTS, get_insight  # noqa: E402

st.set_page_config(page_title="IP Insight 분석기", page_icon="📊", layout="wide")


# ---------------------------------------------------------------------------
# 사이드바 — 설정
# ---------------------------------------------------------------------------
def sidebar() -> None:
    st.sidebar.title("⚙️ 설정")

    st.sidebar.subheader("🤖 LLM (Dataiku 허용 목록)")
    labels = [label for label, _ in ALLOWED_LLM_CANDIDATES]
    ids = [llm_id for _, llm_id in ALLOWED_LLM_CANDIDATES]
    default_idx = ids.index(settings.llm_id) if settings.llm_id in ids else 0
    choice = st.sidebar.selectbox("모델 선택", labels, index=default_idx)
    settings.set_llm_id(ids[labels.index(choice)])
    st.sidebar.caption(f"LLM ID: `{settings.llm_id}`")
    st.sidebar.caption(
        "실행 환경: "
        + ("Dataiku LLM Mesh ✅" if llm.is_dataiku() else "로컬(OpenAI 폴백/데모)")
    )

    if not llm.is_dataiku():
        with st.sidebar.expander("로컬 개발용 OpenAI 폴백(선택)"):
            key = st.text_input("OPENAI_API_KEY", value=settings.openai_api_key, type="password")
            model = st.text_input("OpenAI 모델", value=settings.openai_model)
            if key:
                settings.openai_api_key = key
            settings.openai_model = model or settings.openai_model

    st.sidebar.divider()
    st.sidebar.subheader("📁 저장 위치 (Dataiku)")
    st.sidebar.caption(f"환경: {'Dataiku' if dataiku_io.is_dataiku() else '로컬(폴백)'}")
    st.sidebar.caption(f"입력: {dataiku_io.location_hint('input')}")
    st.sidebar.caption(f"출력: {dataiku_io.location_hint('output')}")


# ---------------------------------------------------------------------------
# 인사이트 선택 UI
# ---------------------------------------------------------------------------
def insight_picker() -> list:
    st.subheader("2️⃣ 도출할 인사이트 선택")
    st.caption("각 인사이트에 '포함하면 좋은 추천 항목'을 함께 안내합니다.")
    selected = []
    cols = st.columns(2)
    for i, ins in enumerate(INSIGHTS):
        with cols[i % 2]:
            checked = st.checkbox(f"**{ins.name}**", value=(ins.id != "citation"), key=f"chk_{ins.id}")
            with st.expander("추천 항목 보기"):
                st.markdown(f"*목표: {ins.goal}*")
                st.markdown(ins.items_bullets())
            if checked:
                selected.append(ins.id)
    return selected


# ---------------------------------------------------------------------------
# 결과 렌더링
# ---------------------------------------------------------------------------
def render_results(out: service.RunOutput) -> None:
    st.success(
        f"분석 완료 · 입력 저장: `{out.input_path}` · 결과 저장: `{out.output_path}`"
    )

    ov = out.overview
    m = st.columns(4)
    m[0].metric("총 특허 건수", ov.get("total_records", "N/A"))
    yr = ov.get("year_range")
    m[1].metric("연도 범위", f"{yr[0]}~{yr[1]}" if yr else "N/A")
    m[2].metric("고유 출원인", ov.get("unique_assignees", "N/A"))
    m[3].metric("고유 발명자", ov.get("unique_inventors", "N/A"))

    st.divider()
    for res in out.results:
        with st.container(border=True):
            st.markdown(f"### {res.name}")
            if res.error:
                st.error(f"분석 오류: {res.error}")
                continue
            if res.summary:
                st.info(res.summary)
            _render_stats_chart(res.stats)
            for item in res.items:
                st.markdown(f"**▪ {item.get('title','')}**")
                st.write(item.get("content", ""))


def _render_stats_chart(stats: dict) -> None:
    if not isinstance(stats, dict):
        return
    yc = stats.get("year_counts")
    if isinstance(yc, dict) and yc:
        st.bar_chart(pd.Series(yc, name="건수"))
        return
    for key in ("top_assignees", "top_ipc", "top_dwpi_class", "top_countries", "top_inventors"):
        pairs = stats.get(key)
        if isinstance(pairs, list) and pairs:
            s = pd.Series({str(k): v for k, v in pairs}, name="건수")
            st.bar_chart(s)
            return


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> None:
    sidebar()
    st.title("📊 IP Insight 분석기")
    st.caption("Derwent DWPI 특허 엑셀 업로드 → ChatGPT 기반 인사이트 → PPT 리포트")

    # 1) 업로드
    st.subheader("1️⃣ 특허 엑셀 업로드")
    uploaded = st.file_uploader("DWPI 포함 특허 엑셀 (.xlsx / .xls)", type=["xlsx", "xls"])

    if uploaded is None:
        st.info("엑셀 파일을 업로드하면 컬럼 자동 인식 후 분석을 시작할 수 있습니다.")
        st.stop()

    file_bytes = uploaded.getvalue()
    try:
        raw = data_loader.read_excel(file_bytes)
    except Exception as exc:
        st.error(f"엑셀을 읽지 못했습니다: {exc}")
        st.stop()

    mapping = data_loader.detect_mapping(raw)
    with st.expander(f"미리보기 & 컬럼 매핑 (총 {len(raw)}행, 인식 {len(mapping)}개 컬럼)", expanded=True):
        st.dataframe(raw.head(10), use_container_width=True)
        if mapping:
            st.markdown("**자동 인식된 컬럼 매핑** (원본 → 정규명)")
            st.table(pd.DataFrame(
                [{"원본 컬럼": k, "정규 컬럼": v} for k, v in mapping.items()]
            ))
        else:
            st.warning("표준 특허/DWPI 컬럼을 자동 인식하지 못했습니다. 분석 품질이 낮을 수 있습니다.")

    # 2) 인사이트 선택
    selected = insight_picker()

    # 3) 실행
    st.subheader("3️⃣ 분석 실행")
    if llm.get_client() is None:
        st.warning(
            "사용 가능한 LLM이 없어 데모(자리표시자) 결과가 생성됩니다. "
            "Dataiku LLM 또는 로컬 OPENAI_API_KEY를 설정하세요."
        )
    else:
        st.caption(f"사용 LLM: `{settings.llm_id}`")
    if st.button("🚀 인사이트 분석 & PPT 생성", type="primary", disabled=not selected):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with st.spinner("분석 중… (선택한 인사이트 수에 따라 시간이 걸립니다)"):
            out = service.run_analysis(
                file_bytes=file_bytes,
                original_filename=uploaded.name,
                insight_ids=selected,
                stamp=stamp,
                mapping=mapping,
            )
        st.session_state["out"] = out

    out = st.session_state.get("out")
    if out is not None:
        render_results(out)
        st.download_button(
            "⬇️ PPT 리포트 다운로드",
            data=out.ppt_bytes,
            file_name=os.path.basename(out.output_path),
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary",
        )


if __name__ == "__main__":
    main()
