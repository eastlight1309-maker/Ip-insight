"""엑셀 번역기 애플리케이션 설정.

IP Insight 앱과 동일한 Dataiku LLM Mesh 허용 목록을 사용한다.
Dataiku 환경변수 / OS 환경변수 순으로 값을 읽으며, 로컬 개발에서도 그대로 동작하도록
안전한 기본값을 제공한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

# =========================================================================
# 데이터이쿠(Dataiku)에서 사용 허용된 LLM 목록 (IP Insight 앱과 동일)
#   (표시명, LLM Mesh ID)  — ID는 project.get_llm(id) 로 호출한다.
# =========================================================================
ALLOWED_LLM_CANDIDATES: List[Tuple[str, str]] = [
    ("gpt-5.3-chat | dw-aoai-chat-eastus2-cognitiv", "azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.3-chat"),
    ("gpt-5.4-nano | dw-aoai-chat-eastus2-cognitiv", "azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4-nano"),
    ("gpt-5.4-mini | dw-aoai-chat-eastus2-cognitiv", "azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4-mini"),
    ("gpt-5.4 | dw-aoai-chat-eastus2-cognitiv", "azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4"),
]

LLM_LABEL_TO_ID = {label: llm_id for label, llm_id in ALLOWED_LLM_CANDIDATES}
LLM_ID_TO_LABEL = {llm_id: label for label, llm_id in ALLOWED_LLM_CANDIDATES}
ALLOWED_LLM_IDS = [llm_id for _, llm_id in ALLOWED_LLM_CANDIDATES]
DEFAULT_LLM_ID = ALLOWED_LLM_CANDIDATES[0][1]

# =========================================================================
# 지원 언어 (출발/도착 언어 선택)
#   코드 -> (한글 표시명, LLM 프롬프트용 영문 이름)
# =========================================================================
LANGUAGES: Dict[str, Tuple[str, str]] = {
    "ko": ("한국어", "Korean"),
    "zh": ("중국어", "Chinese (Simplified)"),
    "ja": ("일본어", "Japanese"),
    "en": ("영어", "English"),
}
# "자동 감지" 출발 언어 옵션 코드
AUTO_DETECT = "auto"


def language_label(code: str) -> str:
    """언어 코드 -> 한글 표시명."""
    if code == AUTO_DETECT:
        return "자동 감지"
    return LANGUAGES.get(code, (code, code))[0]


def language_english_name(code: str) -> str:
    """언어 코드 -> LLM 프롬프트용 영문 이름."""
    if code == AUTO_DETECT:
        return "the source language (auto-detect it)"
    return LANGUAGES.get(code, (code, code))[1]


def _get(key: str, default: str = "") -> str:
    """OS 환경변수 우선, 없으면 default."""
    return os.environ.get(key, default)


@dataclass
class Settings:
    # --- LLM (Dataiku LLM Mesh) ---
    llm_id: str = DEFAULT_LLM_ID
    llm_temperature: float = 0.0  # 번역은 결정론적 결과를 위해 낮게
    llm_max_tokens: int = 2000

    # --- 로컬 개발용 OpenAI 폴백 (Dataiku 밖에서만 사용, 선택) ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # --- Dataiku 관리 폴더 (이름 또는 ID로 지정 가능) ---
    # 프로젝트별로 하위 경로(<project>/...)에 파일을 저장한다.
    input_folder_ref: str = "excel_translator_input"    # 업로드된 원본 엑셀 저장
    output_folder_ref: str = "excel_translator_output"  # 번역 결과 엑셀 저장

    # --- 로컬 폴백 경로 (Dataiku 밖에서 실행 시) ---
    local_input_dir: str = "./data/translator_input"
    local_output_dir: str = "./data/translator_output"

    # --- 번역 배치 설정 ---
    # 한 번의 LLM 호출에 담을 셀(문자열) 최대 개수
    batch_size: int = 20

    def set_llm_id(self, llm_id: str) -> None:
        """허용 목록 내에서만 LLM을 설정한다."""
        if llm_id in ALLOWED_LLM_IDS:
            self.llm_id = llm_id

    @classmethod
    def load(cls) -> "Settings":
        env_llm = _get("DKU_LLM_ID", "")
        return cls(
            llm_id=env_llm if env_llm in ALLOWED_LLM_IDS else DEFAULT_LLM_ID,
            llm_temperature=float(_get("LLM_TEMPERATURE", "0.0")),
            llm_max_tokens=int(_get("LLM_MAX_TOKENS", "2000")),
            openai_api_key=_get("OPENAI_API_KEY", ""),
            openai_model=_get("OPENAI_MODEL", "gpt-4o"),
            input_folder_ref=_get(
                "DKU_TRANSLATOR_INPUT_FOLDER",
                _get("DKU_TRANSLATOR_INPUT_FOLDER_ID", "excel_translator_input"),
            ),
            output_folder_ref=_get(
                "DKU_TRANSLATOR_OUTPUT_FOLDER",
                _get("DKU_TRANSLATOR_OUTPUT_FOLDER_ID", "excel_translator_output"),
            ),
            local_input_dir=_get("LOCAL_TRANSLATOR_INPUT_DIR", "./data/translator_input"),
            local_output_dir=_get("LOCAL_TRANSLATOR_OUTPUT_DIR", "./data/translator_output"),
            batch_size=int(_get("TRANSLATOR_BATCH_SIZE", "20")),
        )


settings = Settings.load()
