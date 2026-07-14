"""IP 인사이트 카탈로그.

각 인사이트의 정의, 필요한 데이터 컬럼, "포함하면 좋은 추천 항목",
그리고 LLM 프롬프트 골격을 한 곳에서 관리한다.
프론트엔드/백엔드/PPT 생성기가 모두 이 카탈로그를 참조한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Insight:
    """단일 인사이트 정의."""

    id: str
    name: str  # 한글 표시명
    goal: str  # 이 인사이트로 답하고자 하는 핵심 질문
    # 이 인사이트를 도출하는 데 도움이 되는 (정규화된) 컬럼들
    helpful_columns: List[str] = field(default_factory=list)
    # 사용자에게 추천하는 "이 인사이트에 담기면 좋은 항목"
    recommended_items: List[str] = field(default_factory=list)

    def items_bullets(self) -> str:
        return "\n".join(f"- {item}" for item in self.recommended_items)


# ---------------------------------------------------------------------------
# 인사이트 카탈로그
# ---------------------------------------------------------------------------
INSIGHTS: List[Insight] = [
    Insight(
        id="tech_trend",
        name="기술 트렌드 분석",
        goal="시간에 따른 출원 흐름과 부상/쇠퇴 기술을 파악한다.",
        helpful_columns=["priority_date", "publication_date", "application_date", "ipc", "dwpi_class"],
        recommended_items=[
            "연도별 출원 건수 추이 (그래프)",
            "급성장 / 급감 기술 영역",
            "최근 3년간 새롭게 부상한(Emerging) 기술",
            "기술 성숙도 단계 (도입기·성장기·성숙기·쇠퇴기)",
            "향후 3~5년 기술 전망 및 시사점",
        ],
    ),
    Insight(
        id="key_players",
        name="주요 출원인 / 경쟁사 분석",
        goal="누가 이 기술 영역을 주도하는지, 경쟁 구도는 어떤지 파악한다.",
        helpful_columns=["assignee", "dwpi_assignee", "publication_number", "ipc"],
        recommended_items=[
            "상위 출원인 Top 10과 점유율",
            "출원인별 핵심 기술 집중 영역",
            "신규 진입자(최근 등장 출원인)",
            "공동출원 / 협력 관계",
            "경쟁 강도(집중도) 평가",
        ],
    ),
    Insight(
        id="classification",
        name="기술 분류(Landscape) 분포",
        goal="포트폴리오가 어떤 기술 분류에 분포하는지 지도화한다.",
        helpful_columns=["ipc", "cpc", "dwpi_class", "dwpi_manual_code"],
        recommended_items=[
            "상위 IPC / CPC 분류와 건수",
            "DWPI Class Code / Manual Code 분포",
            "기술 분류 간 융합(공동 분류) 패턴",
            "핵심 기술 vs 주변 기술 구분",
            "분류 기반 기술 지형도 요약",
        ],
    ),
    Insight(
        id="core_themes",
        name="핵심 기술 테마 / 클러스터",
        goal="DWPI 초록에서 반복되는 핵심 기술 주제를 추출한다.",
        helpful_columns=["dwpi_title", "dwpi_abstract", "title", "abstract"],
        recommended_items=[
            "주요 기술 클러스터(테마) 5~8개",
            "각 테마의 대표 특허(공개번호)",
            "테마별 해결 과제 (Novelty / Problem)",
            "테마별 기술적 효과 (Advantage / Use)",
            "테마 간 연관성 / 융합 가능성",
        ],
    ),
    Insight(
        id="white_space",
        name="공백 기술 / 기회 분석",
        goal="경쟁이 적고 성장 가능성이 높은 기회 영역을 찾는다.",
        helpful_columns=["ipc", "dwpi_class", "priority_date", "assignee"],
        recommended_items=[
            "미개척(White space) 기술 영역",
            "저경쟁·고성장 기회 영역",
            "진입 시 확보 가능한 포지션",
            "진입 리스크 및 선결 과제",
            "우선 검토 권고 영역",
        ],
    ),
    Insight(
        id="inventor",
        name="발명자 / R&D 역량 분석",
        goal="핵심 인재와 R&D 생산성을 파악한다.",
        helpful_columns=["inventor", "assignee", "publication_number"],
        recommended_items=[
            "핵심 발명자(Star inventor) Top 10",
            "발명자–출원인 매핑 및 팀 구조",
            "출원인별 R&D 생산성(발명자당 출원 수)",
            "핵심 발명자의 기술 전문 영역",
            "인재 확보 / 유출 시사점",
        ],
    ),
    Insight(
        id="geography",
        name="지역 / 시장(패밀리) 분석",
        goal="어느 국가·시장을 겨냥하는지 파악한다.",
        helpful_columns=["country", "publication_number", "assignee", "family_id"],
        recommended_items=[
            "특허청/국가별 출원 분포",
            "주요 타겟 시장",
            "패밀리 확장(다국가 출원) 전략 패턴",
            "지역별 경쟁 강도 차이",
            "시장 진입 우선순위 시사점",
        ],
    ),
    Insight(
        id="citation",
        name="인용 / 영향력 분석",
        goal="기술적으로 영향력 있는 핵심 특허를 식별한다.",
        helpful_columns=["cited_refs", "citing_patents", "publication_number", "assignee"],
        recommended_items=[
            "피인용 상위 핵심 특허",
            "기술 영향력(허브 특허) 요약",
            "인용 관계 기반 기술 흐름",
            "출원인별 기술 영향력 비교",
            "라이선싱/회피설계 관점 시사점",
        ],
    ),
    Insight(
        id="portfolio_strength",
        name="포트폴리오 강점 / 리스크",
        goal="포트폴리오의 강·약점과 전략적 시사점을 진단한다.",
        helpful_columns=["ipc", "dwpi_class", "assignee", "priority_date"],
        recommended_items=[
            "강점 기술 영역",
            "취약 / 리스크 기술 영역",
            "경쟁사 대비 상대적 포지션",
            "라이선싱 / M&A / 협력 시사점",
            "포트폴리오 강화 전략 제언",
        ],
    ),
    Insight(
        id="executive_summary",
        name="종합 요약 (Executive Summary)",
        goal="경영진 관점의 핵심 발견과 권고를 한 장에 정리한다.",
        helpful_columns=[],
        recommended_items=[
            "핵심 발견 사항 3~5가지",
            "전략적 시사점",
            "즉시 실행 권고 사항",
            "중장기 검토 과제",
            "핵심 리스크 및 대응 방향",
        ],
    ),
]

INSIGHTS_BY_ID = {ins.id: ins for ins in INSIGHTS}


def get_insight(insight_id: str) -> Insight:
    return INSIGHTS_BY_ID[insight_id]


def all_insight_ids() -> List[str]:
    return [ins.id for ins in INSIGHTS]
