"""IP Insight 백엔드 패키지.

프론트엔드(Streamlit)는 이 패키지의 `service`, `insights`, `data_loader`,
`dataiku_io` 모듈만 알면 되도록 계층을 분리했다.
"""

from . import (  # noqa: F401
    analytics,
    config,
    data_loader,
    dataiku_io,
    insights,
    llm_analyzer,
    ppt_builder,
    service,
)

__all__ = [
    "analytics",
    "config",
    "data_loader",
    "dataiku_io",
    "insights",
    "llm_analyzer",
    "ppt_builder",
    "service",
]
