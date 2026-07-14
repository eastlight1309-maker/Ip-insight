"""엑셀 번역기 백엔드 패키지.

프론트엔드(Streamlit)는 이 패키지의 `service`, `excel_io`, `dataiku_io`,
`config` 모듈만 알면 되도록 계층을 분리했다.

패키지명을 `backend` 로 두지 않는 이유는 Dataiku 웹앱 실행 폴더
`backend/main.py` 와 충돌하기 때문이다(IP Insight 앱과 동일한 이유).
"""

from . import (  # noqa: F401
    config,
    dataiku_io,
    excel_io,
    llm,
    service,
    translator,
)

__all__ = [
    "config",
    "dataiku_io",
    "excel_io",
    "llm",
    "service",
    "translator",
]
