"""Streamlit UI 스캐폴드.

앱 기능이 정의되면 이 모듈을 중심으로 화면을 확장한다.
"""

import streamlit as st

from iplandscape.config import APP_TITLE


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="📈", layout="wide")
    st.title(f"📈 {APP_TITLE}")
    st.caption("특허 데이터 기반 IP 랜드스케이프 차트 생성 웹앱 — 개발 준비 중")

    uploaded = st.file_uploader(
        "특허 엑셀 파일 업로드 (.xlsx)", type=["xlsx"], accept_multiple_files=False
    )
    if uploaded is not None:
        st.info("차트 생성 기능은 아직 구현되지 않았습니다. 로드맵은 README를 참고하세요.")


if __name__ == "__main__":
    main()
