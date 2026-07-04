"""ChatGPT(OpenAI) API 연동 — 인사이트별 분석 생성.

각 인사이트에 대해 (1) 정량 통계와 (2) 초록 샘플을 컨텍스트로 주고,
insights.py 의 '추천 항목'을 채우도록 구조화된 JSON을 요청한다.

OPENAI_API_KEY 가 없으면 오프라인 데모용 mock 결과를 반환해
UI/PPT 파이프라인을 API 없이도 검증할 수 있다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from . import analytics
from .config import settings
from .insights import Insight, get_insight


@dataclass
class InsightResult:
    insight_id: str
    name: str
    summary: str  # 2~3문장 요약
    items: List[Dict[str, str]] = field(default_factory=list)  # [{"title":..,"content":..}]
    stats: Dict[str, object] = field(default_factory=dict)  # 차트용 정량 데이터
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "insight_id": self.insight_id,
            "name": self.name,
            "summary": self.summary,
            "items": self.items,
            "stats": self.stats,
            "error": self.error,
        }


SYSTEM_PROMPT = (
    "당신은 특허/지식재산 전략 분석 전문가입니다. "
    "Derwent DWPI를 포함한 특허 데이터로부터 실무적으로 유용한 인사이트를 도출합니다. "
    "제공된 데이터 근거에만 기반해 분석하고, 데이터에 없는 사실을 지어내지 마십시오. "
    "모든 답변은 한국어로 작성합니다."
)


def _user_prompt(insight: Insight, stats: Dict[str, object]) -> str:
    item_lines = "\n".join(f'  - "{it}"' for it in insight.recommended_items)
    stats_json = json.dumps(stats, ensure_ascii=False, default=str)[:12000]
    return f"""[분석 인사이트] {insight.name}
[목표] {insight.goal}

[데이터 정량 요약 / 초록 샘플 (JSON)]
{stats_json}

아래 '추천 항목' 각각에 대해 데이터 근거를 바탕으로 분석 내용을 작성하세요.
추천 항목:
{item_lines}

반드시 아래 JSON 형식으로만 응답하세요(설명 텍스트 금지):
{{
  "summary": "핵심 요약 2~3문장",
  "items": [
    {{"title": "추천 항목 제목", "content": "해당 항목에 대한 분석(수치/근거 포함, 3~6문장)"}}
  ]
}}
items 는 위 추천 항목 순서대로 모두 포함하세요."""


def _get_client():
    """OpenAI 클라이언트 생성. 실패하면 None."""
    api_key = settings.openai_api_key
    if not api_key:
        return None
    try:
        from openai import OpenAI  # openai>=1.0

        return OpenAI(api_key=api_key)
    except Exception:
        return None


def _mock_result(insight: Insight, stats: Dict[str, object]) -> InsightResult:
    items = [
        {
            "title": it,
            "content": "(데모 모드) OPENAI_API_KEY 미설정 상태입니다. "
            "API 키를 설정하면 데이터 기반 실제 분석이 채워집니다.",
        }
        for it in insight.recommended_items
    ]
    return InsightResult(
        insight_id=insight.id,
        name=insight.name,
        summary=f"[데모] '{insight.name}' 분석 자리표시자입니다. API 키 설정 후 재실행하세요.",
        items=items,
        stats=stats,
    )


def _parse_json(text: str) -> Dict[str, object]:
    """모델 응답에서 JSON 블록 추출/파싱."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def analyze_insight(insight_id: str, df: pd.DataFrame, client=None) -> InsightResult:
    """단일 인사이트 분석."""
    insight = get_insight(insight_id)
    stats = analytics.stats_for_insight(insight_id, df)

    client = client if client is not None else _get_client()
    if client is None:
        return _mock_result(insight, stats)

    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(insight, stats)},
            ],
        )
        content = resp.choices[0].message.content or ""
        parsed = _parse_json(content)
        return InsightResult(
            insight_id=insight.id,
            name=insight.name,
            summary=str(parsed.get("summary", "")).strip(),
            items=[
                {"title": str(it.get("title", "")), "content": str(it.get("content", ""))}
                for it in parsed.get("items", [])
                if isinstance(it, dict)
            ],
            stats=stats,
        )
    except Exception as exc:  # 네트워크/파싱/키 오류 등
        return InsightResult(
            insight_id=insight.id,
            name=insight.name,
            summary="",
            items=[],
            stats=stats,
            error=f"{type(exc).__name__}: {exc}",
        )


def analyze(insight_ids: List[str], df: pd.DataFrame) -> List[InsightResult]:
    """여러 인사이트 순차 분석 (클라이언트 재사용)."""
    client = _get_client()
    return [analyze_insight(iid, df, client=client) for iid in insight_ids]
