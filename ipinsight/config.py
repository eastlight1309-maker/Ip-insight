"""애플리케이션 설정.

Dataiku 환경변수 / 프로젝트 변수 / OS 환경변수 순으로 값을 읽는다.
로컬 개발에서도 그대로 동작하도록 안전한 기본값을 제공한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple

# =========================================================================
# 데이터이쿠(Dataiku)에서 사용 허용된 LLM 목록 (고정)
#   (표시명, LLM Mesh ID)  — ID는 project.get_llm(id) 로 호출한다.
# =========================================================================
ALLOWED_LLM_CANDIDATES: List[Tuple[str, str]] = [
    ("gpt-5.3-chat | dw-aoai-chat-eastus2-cognitiv", "azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.3-chat"),
    ("gpt-5.4-nano | dw-aoai-chat-eastus2-cognitiv", "azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4-nano"),
    ("gpt-5.4-mini | dw-aoai-chat-eastus2-cognitiv", "azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4-mini"),
    ("gpt-5.4 | dw-aoai-chat-eastus2-cognitiv", "azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4"),
]

# 라벨 -> ID / ID -> 라벨 조회용
LLM_LABEL_TO_ID = {label: llm_id for label, llm_id in ALLOWED_LLM_CANDIDATES}
LLM_ID_TO_LABEL = {llm_id: label for label, llm_id in ALLOWED_LLM_CANDIDATES}
ALLOWED_LLM_IDS = [llm_id for _, llm_id in ALLOWED_LLM_CANDIDATES]
DEFAULT_LLM_ID = ALLOWED_LLM_CANDIDATES[0][1]


def _get(key: str, default: str = "") -> str:
    """OS 환경변수 우선, 없으면 default."""
    return os.environ.get(key, default)


@dataclass
class Settings:
    # --- LLM (Dataiku LLM Mesh) ---
    # 실제 호출 대상. 반드시 ALLOWED_LLM_IDS 중 하나여야 한다.
    llm_id: str = DEFAULT_LLM_ID
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1800

    # --- 로컬 개발용 OpenAI 폴백 (Dataiku 밖에서만 사용, 선택) ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # --- Dataiku 관리 폴더 (이름 또는 ID로 지정 가능) ---
    # dataiku.Folder(ref) 는 폴더 이름 또는 ID 모두 허용한다.
    input_folder_ref: str = "ip_insight_input"    # 업로드된 엑셀 원본 저장
    output_folder_ref: str = "ip_insight_output"  # 생성된 PPT / 분석결과 저장

    # --- 로컬 폴백 경로 (Dataiku 밖에서 실행 시) ---
    local_input_dir: str = "./data/input"
    local_output_dir: str = "./data/output"

    # 분석 시 LLM 프롬프트에 넣을 초록 샘플 최대 개수
    abstract_sample_size: int = 40

    def set_llm_id(self, llm_id: str) -> None:
        """허용 목록 내에서만 LLM을 설정한다."""
        if llm_id in ALLOWED_LLM_IDS:
            self.llm_id = llm_id

    @classmethod
    def load(cls) -> "Settings":
        env_llm = _get("DKU_LLM_ID", "")
        return cls(
            llm_id=env_llm if env_llm in ALLOWED_LLM_IDS else DEFAULT_LLM_ID,
            llm_temperature=float(_get("LLM_TEMPERATURE", "0.3")),
            llm_max_tokens=int(_get("LLM_MAX_TOKENS", "1800")),
            openai_api_key=_get("OPENAI_API_KEY", ""),
            openai_model=_get("OPENAI_MODEL", "gpt-4o"),
            # 이름 우선(DKU_INPUT_FOLDER), 없으면 ID(DKU_INPUT_FOLDER_ID), 없으면 기본 이름
            input_folder_ref=_get("DKU_INPUT_FOLDER", _get("DKU_INPUT_FOLDER_ID", "ip_insight_input")),
            output_folder_ref=_get("DKU_OUTPUT_FOLDER", _get("DKU_OUTPUT_FOLDER_ID", "ip_insight_output")),
            local_input_dir=_get("LOCAL_INPUT_DIR", "./data/input"),
            local_output_dir=_get("LOCAL_OUTPUT_DIR", "./data/output"),
            abstract_sample_size=int(_get("ABSTRACT_SAMPLE_SIZE", "40")),
        )


settings = Settings.load()
