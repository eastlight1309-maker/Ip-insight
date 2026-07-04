"""정량 통계 계산.

LLM에 넘길 컨텍스트와 PPT 차트에 쓰일 집계를 계산한다.
컬럼이 없으면 조용히 빈 결과를 반환해 어떤 데이터셋에도 견고하게 동작한다.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd


def _explode_multi(series: pd.Series, seps: Tuple[str, ...] = (";", "|", ",", "//")) -> pd.Series:
    """한 셀에 여러 값(예: 'A; B; C')이 들어있는 컬럼을 개별 값으로 분해."""
    s = series.dropna().astype(str)
    for sep in seps:
        s = s.str.replace(sep, "␟", regex=False)
    exploded = s.str.split("␟").explode().str.strip()
    return exploded[exploded != ""]


def year_counts(df: pd.DataFrame, date_col: str = "priority_date") -> Dict[int, int]:
    if date_col not in df.columns:
        return {}
    years = pd.to_datetime(df[date_col], errors="coerce").dt.year.dropna().astype(int)
    return {int(k): int(v) for k, v in years.value_counts().sort_index().items()}


def top_values(df: pd.DataFrame, col: str, n: int = 10, multi: bool = False) -> List[Tuple[str, int]]:
    if col not in df.columns:
        return []
    series = _explode_multi(df[col]) if multi else df[col].dropna().astype(str).str.strip()
    series = series[series != ""]
    if series.empty:
        return []
    return [(str(k), int(v)) for k, v in series.value_counts().head(n).items()]


def ipc_prefixes(df: pd.DataFrame, col: str = "ipc", n: int = 12, level: int = 4) -> List[Tuple[str, int]]:
    """IPC 코드를 상위 level 자리(예: 'H01L')로 잘라 집계."""
    if col not in df.columns:
        return []
    series = _explode_multi(df[col]).str.replace(" ", "", regex=False).str.upper()
    series = series.str[:level]
    series = series[series.str.len() > 0]
    if series.empty:
        return []
    return [(str(k), int(v)) for k, v in series.value_counts().head(n).items()]


def sample_abstracts(df: pd.DataFrame, n: int = 40) -> List[str]:
    """LLM 테마 분석용 초록 샘플. DWPI 초록 우선, 없으면 일반 초록/제목."""
    for col in ("dwpi_abstract", "abstract", "dwpi_title", "title"):
        if col in df.columns:
            vals = df[col].dropna().astype(str).str.strip()
            vals = vals[vals != ""]
            if not vals.empty:
                return vals.head(n).tolist()
    return []


def overview(df: pd.DataFrame) -> Dict[str, object]:
    """데이터셋 전반 요약."""
    return {
        "total_records": int(len(df)),
        "columns_present": list(df.columns),
        "year_range": _year_range(df),
        "unique_assignees": _nunique(df, "assignee") or _nunique(df, "dwpi_assignee"),
        "unique_inventors": _nunique(df, "inventor"),
    }


def _nunique(df: pd.DataFrame, col: str) -> Optional[int]:
    if col not in df.columns:
        return None
    return int(_explode_multi(df[col]).nunique())


def _year_range(df: pd.DataFrame) -> Optional[Tuple[int, int]]:
    yc = year_counts(df)
    if not yc:
        return None
    return (min(yc), max(yc))


def stats_for_insight(insight_id: str, df: pd.DataFrame) -> Dict[str, object]:
    """인사이트별 관련 정량 통계 묶음."""
    base: Dict[str, object] = {"overview": overview(df)}

    if insight_id == "tech_trend":
        base["year_counts"] = year_counts(df)
        base["top_ipc"] = ipc_prefixes(df)
    elif insight_id == "key_players":
        base["top_assignees"] = top_values(df, "assignee", 10, multi=True) or \
            top_values(df, "dwpi_assignee", 10, multi=True)
        base["year_counts"] = year_counts(df)
    elif insight_id == "classification":
        base["top_ipc"] = ipc_prefixes(df)
        base["top_cpc"] = top_values(df, "cpc", 10, multi=True)
        base["top_dwpi_class"] = top_values(df, "dwpi_class", 10, multi=True)
    elif insight_id == "core_themes":
        base["abstracts"] = sample_abstracts(df)
    elif insight_id == "white_space":
        base["top_ipc"] = ipc_prefixes(df)
        base["year_counts"] = year_counts(df)
        base["top_assignees"] = top_values(df, "assignee", 10, multi=True)
    elif insight_id == "inventor":
        base["top_inventors"] = top_values(df, "inventor", 10, multi=True)
        base["top_assignees"] = top_values(df, "assignee", 10, multi=True)
    elif insight_id == "geography":
        base["top_countries"] = top_values(df, "country", 12, multi=True)
    elif insight_id == "citation":
        base["top_cited"] = top_values(df, "citing_patents", 10, multi=True)
    elif insight_id == "portfolio_strength":
        base["top_ipc"] = ipc_prefixes(df)
        base["top_assignees"] = top_values(df, "assignee", 10, multi=True)
        base["year_counts"] = year_counts(df)
    elif insight_id == "executive_summary":
        base["top_assignees"] = top_values(df, "assignee", 8, multi=True)
        base["top_ipc"] = ipc_prefixes(df, n=8)
        base["year_counts"] = year_counts(df)

    return base
