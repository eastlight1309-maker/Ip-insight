"""엑셀 번역기 — Streamlit UI (패키지 내부 모듈).

UI 코드를 패키지 안에 두어, Dataiku 웹앱 편집기에는 아래 2줄만 넣으면 되게 한다:

    from exceltranslator.webapp import main
    main()

이렇게 하면 UI를 수정해도(프로젝트 라이브러리만 갱신) 웹앱 편집기 코드는 그대로 유지된다.
로컬 개발에서는 `streamlit run frontend/translator_app.py` 가 이 main() 을 호출한다.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from . import dataiku_io, excel_io, llm, service
from .config import (
    ALLOWED_LLM_CANDIDATES,
    AUTO_DETECT,
    LANGUAGES,
    language_label,
    settings,
)

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---------------------------------------------------------------------------
# Streamlit 버전 호환 헬퍼
#   신/구 Streamlit 모두에서 안전하게 표를 그린다. (use_container_width 는
#   2025-12-31 이후 제거 예정이라 최신 버전에서 예외가 날 수 있음)
# ---------------------------------------------------------------------------
def _show_df(df) -> None:
    try:
        st.dataframe(df, width="stretch")          # 최신 Streamlit
    except TypeError:
        try:
            st.dataframe(df, use_container_width=True)  # 구 Streamlit
        except TypeError:
            st.dataframe(df)                        # 최소 폴백


def _divider() -> None:
    """st.divider() 는 Streamlit 1.23+ 에서만 존재 → 구버전은 markdown 폴백."""
    fn = getattr(st, "divider", None)
    if callable(fn):
        fn()
    else:
        st.markdown("---")


class _Progress:
    """text 인자 유무와 관계없이 안전하게 동작하는 진행바 래퍼."""

    def __init__(self, text: str = ""):
        try:
            self._bar = st.progress(0.0, text=text)
        except TypeError:
            self._bar = st.progress(0.0)

    def update(self, frac: float, text: str = "") -> None:
        frac = max(0.0, min(1.0, frac))
        try:
            self._bar.progress(frac, text=text)
        except TypeError:
            self._bar.progress(frac)


# ---------------------------------------------------------------------------
# 사이드바 — 설정
# ---------------------------------------------------------------------------
def model_picker(container=None) -> str:
    """LLM 모델 선택기. 본문/사이드바 어디서든 재사용 가능.

    container 를 주면 그 컨테이너(예: st.sidebar) 에, 없으면 현재 위치(본문)에 렌더링.
    선택 결과를 settings 에 반영하고 선택된 LLM ID 를 반환한다.
    """
    ui = container if container is not None else st
    labels = [label for label, _ in ALLOWED_LLM_CANDIDATES]
    ids = [llm_id for _, llm_id in ALLOWED_LLM_CANDIDATES]
    default_idx = ids.index(settings.llm_id) if settings.llm_id in ids else 0
    choice = ui.selectbox("🤖 LLM 모델 (Dataiku 허용 목록)", labels, index=default_idx, key="llm_model")
    settings.set_llm_id(ids[labels.index(choice)])
    ui.caption(f"LLM ID: `{settings.llm_id}`")
    return settings.llm_id


def sidebar() -> None:
    st.sidebar.title("⚙️ 설정")

    st.sidebar.caption(
        "실행 환경: "
        + ("Dataiku LLM Mesh ✅" if llm.is_dataiku() else "로컬(OpenAI 폴백/데모)")
    )
    st.sidebar.caption(f"현재 LLM: `{settings.llm_id}`")
    st.sidebar.caption("모델 선택은 '🆕 새 번역' 탭의 **번역 설정**에서 합니다.")

    if not llm.is_dataiku():
        with st.sidebar.expander("로컬 개발용 OpenAI 폴백(선택)"):
            key = st.text_input("OPENAI_API_KEY", value=settings.openai_api_key, type="password")
            model = st.text_input("OpenAI 모델", value=settings.openai_model)
            if key:
                settings.openai_api_key = key
            settings.openai_model = model or settings.openai_model

    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 저장 위치 (Dataiku)")
    st.sidebar.caption(f"환경: {'Dataiku' if dataiku_io.is_dataiku() else '로컬(폴백)'}")
    st.sidebar.caption(f"입력 폴더: {dataiku_io.location_hint('input')}")
    st.sidebar.caption(f"출력 폴더: {dataiku_io.location_hint('output')}")
    st.sidebar.caption("파일은 `<프로젝트명>/` 하위에 저장됩니다.")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Streamlit {getattr(st, '__version__', '?')}")


# ---------------------------------------------------------------------------
# 언어 선택 위젯
# ---------------------------------------------------------------------------
def _language_pickers() -> tuple:
    # format_func 대신, 표시 라벨을 직접 옵션으로 넘겨 버전 호환성을 높인다.
    lang_codes = list(LANGUAGES.keys())

    # 출발 언어: 자동 감지 + 4개 언어
    src_codes = [AUTO_DETECT] + lang_codes
    src_labels = [language_label(c) for c in src_codes]  # ["자동 감지","한국어",...]
    # 도착 언어: 4개 언어
    tgt_codes = list(lang_codes)
    tgt_labels = [language_label(c) for c in tgt_codes]

    c1, c2 = st.columns(2)
    with c1:
        src_label = st.selectbox("출발 언어", src_labels, index=0, key="src_lang")
        src = src_codes[src_labels.index(src_label)]
    with c2:
        # 기본 도착언어는 출발언어와 다르게(한국어→영어)
        default_tgt = tgt_codes.index("en") if src == "ko" else 0
        tgt_label = st.selectbox("도착 언어", tgt_labels, index=default_tgt, key="tgt_lang")
        tgt = tgt_codes[tgt_labels.index(tgt_label)]

    if src != AUTO_DETECT and src == tgt:
        st.warning("출발 언어와 도착 언어가 같습니다. 도착 언어를 다르게 선택하세요.")
    return src, tgt


# ---------------------------------------------------------------------------
# 결과 렌더링
# ---------------------------------------------------------------------------
def _render_result(out: service.RunOutput) -> None:
    st.success(
        f"번역 완료 · {out.row_count}행 · "
        f"입력 저장: `{out.input_path}` · 결과 저장: `{out.output_path}`"
    )
    if out.mode == "demo":
        st.warning(
            "⚠️ 데모 모드로 실행되었습니다(사용 가능한 LLM 없음). "
            "결과는 `[언어] 원문` 형태의 자리표시자입니다."
        )
    st.caption(
        f"번역 컬럼: {', '.join(out.translated_columns) or '없음'} → "
        f"추가된 결과 컬럼: {', '.join(out.new_columns) or '없음'}"
    )
    _show_df(out.df.head(30))

    st.download_button(
        "⬇️ 번역 결과 엑셀 다운로드 (화면에서 저장)",
        data=out.xlsx_bytes,
        file_name=out.output_filename,
        mime=_XLSX_MIME,
        type="primary",
    )


# ---------------------------------------------------------------------------
# 탭 1 — 새 번역
# ---------------------------------------------------------------------------
def tab_new() -> None:
    st.subheader("1️⃣ 프로젝트 & 엑셀 업로드")
    project = st.text_input(
        "프로젝트 이름",
        value=st.session_state.get("project_name", ""),
        placeholder="예: 2026_마케팅_카탈로그",
        help="입력/출력 파일이 이 프로젝트 이름의 하위 폴더에 저장됩니다.",
    )
    if project:
        st.session_state["project_name"] = project

    uploaded = st.file_uploader("번역할 엑셀 업로드 (.xlsx / .xls)", type=["xlsx", "xls"])

    if uploaded is None:
        st.info("프로젝트 이름을 정하고 엑셀 파일을 업로드하세요.")
        return
    if not project or not project.strip():
        st.warning("먼저 프로젝트 이름을 입력하세요.")
        return

    file_bytes = uploaded.getvalue()

    # 시트 선택
    try:
        sheets = excel_io.sheet_names(file_bytes)
    except Exception as exc:
        st.error(f"엑셀을 읽지 못했습니다: {exc}")
        return
    sheet = sheets[0]
    if len(sheets) > 1:
        sheet = st.selectbox("시트 선택", sheets, index=0)

    try:
        df = excel_io.read_excel(file_bytes, sheet)
    except Exception as exc:
        st.error(f"엑셀 시트를 읽지 못했습니다: {exc}")
        return

    with st.expander(f"미리보기 (총 {len(df)}행 · {len(df.columns)}컬럼)", expanded=True):
        _show_df(df.head(10))

    st.subheader("2️⃣ 번역 설정")
    model_picker()          # LLM 모델 선택 (본문)
    src, tgt = _language_pickers()

    columns = st.multiselect(
        "번역할 컬럼 선택 (여러 개 선택 가능 · 결과는 맨 뒤 컬럼으로 추가됨)",
        list(map(str, df.columns)),
        key="cols_to_translate",
    )

    st.subheader("3️⃣ 실행")
    client_available = llm.get_client() is not None
    if not client_available:
        st.warning(
            "사용 가능한 LLM이 없어 데모(자리표시자) 결과가 생성됩니다. "
            "Dataiku LLM 또는 로컬 OPENAI_API_KEY를 설정하세요."
        )
    else:
        st.caption(f"사용 LLM: `{settings.llm_id}`")

    disabled = not columns or (src != AUTO_DETECT and src == tgt)
    if st.button("🚀 번역 실행", type="primary", disabled=disabled):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prog = _Progress("번역 준비 중…")

        def _on_progress(done: int, total: int) -> None:
            frac = (done / total) if total else 1.0
            prog.update(frac, f"번역 중… {done}/{total} 셀")

        with st.spinner("번역 중… (행/컬럼 수에 따라 시간이 걸립니다)"):
            out = service.run_translation(
                file_bytes=file_bytes,
                original_filename=uploaded.name,
                project=project,
                columns=columns,
                src_code=src,
                tgt_code=tgt,
                stamp=stamp,
                sheet_name=sheet,
                progress=_on_progress,
            )
        prog.update(1.0, "완료")
        st.session_state["last_out"] = out

    out = st.session_state.get("last_out")
    if out is not None:
        _divider()
        _render_result(out)


# ---------------------------------------------------------------------------
# 탭 2 — 이전 결과 (히스토리)
# ---------------------------------------------------------------------------
def tab_history() -> None:
    st.subheader("📚 이전 번역 결과 찾기")
    st.caption("출력 폴더에 저장된 프로젝트별 번역 결과를 조회하고 다운로드합니다.")

    projects = dataiku_io.list_projects("output")
    if not projects:
        st.info("아직 저장된 번역 결과가 없습니다. '새 번역' 탭에서 먼저 번역을 실행하세요.")
        return

    # 현재 작업 중인 프로젝트가 있으면 기본 선택
    current = st.session_state.get("project_name")
    default_idx = projects.index(current) if current in projects else 0
    project = st.selectbox("프로젝트 선택", projects, index=default_idx)

    files = dataiku_io.list_files("output", project)
    if not files:
        st.info("이 프로젝트에 저장된 결과 파일이 없습니다.")
        return

    st.caption(f"저장 위치: {dataiku_io.location_hint('output', project)}")

    file = st.selectbox("결과 파일 선택 (최신순)", files)

    data = None
    try:
        data = dataiku_io.read_bytes("output", project, file)
    except Exception as exc:
        st.error(f"파일을 불러오지 못했습니다: {exc}")

    col1, col2 = st.columns([1, 1])
    with col1:
        preview = st.button("👁️ 미리보기", key="hist_preview")
    with col2:
        if data is not None:
            st.download_button(
                "⬇️ 폴더에서 다운로드",
                data=data,
                file_name=file,
                mime=_XLSX_MIME,
                type="primary",
                key="hist_download",
            )

    if preview and data is not None:
        try:
            df = excel_io.read_excel(data)
            _show_df(df.head(30))
        except Exception as exc:
            st.error(f"미리보기 실패: {exc}")

    with st.expander("입력(원본) 파일 목록 보기"):
        in_files = dataiku_io.list_files("input", project)
        if in_files:
            in_file = st.selectbox("원본 파일", in_files, key="hist_input_file")
            try:
                in_data = dataiku_io.read_bytes("input", project, in_file)
                st.download_button(
                    "⬇️ 원본 다운로드",
                    data=in_data,
                    file_name=in_file,
                    mime=_XLSX_MIME,
                    key="hist_input_download",
                )
            except Exception as exc:
                st.error(f"원본을 불러오지 못했습니다: {exc}")
        else:
            st.caption("저장된 원본 파일이 없습니다.")


# ---------------------------------------------------------------------------
# 메인 진입점
# ---------------------------------------------------------------------------
def main() -> None:
    try:
        st.set_page_config(
            page_title="엑셀 번역기",
            page_icon="🌐",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    except Exception:
        # Dataiku 등 일부 환경에서 set_page_config 가 이미 호출됐거나 제한될 수 있음
        pass
    sidebar()
    st.title("🌐 엑셀 번역기")
    st.caption(
        "엑셀 업로드 → 컬럼 선택 → 한/중/일/영 번역 → 결과를 맨 뒤 컬럼에 추가 · "
        "Dataiku LLM Mesh 사용"
    )

    tab1, tab2 = st.tabs(["🆕 새 번역", "📚 이전 결과"])
    with tab1:
        tab_new()
    with tab2:
        tab_history()


if __name__ == "__main__":  # pragma: no cover
    main()
