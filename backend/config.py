"""애플리케이션 설정.

Dataiku 환경변수 / 프로젝트 변수 / OS 환경변수 순으로 값을 읽는다.
로컬 개발에서도 그대로 동작하도록 안전한 기본값을 제공한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get(key: str, default: str = "") -> str:
    """OS 환경변수 우선, 없으면 default."""
    return os.environ.get(key, default)


@dataclass
class Settings:
    # --- OpenAI (ChatGPT) ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 1800

    # --- Dataiku 관리 폴더 ID (DSS Flow에서 생성한 폴더의 ID) ---
    input_folder_id: str = ""   # 업로드된 엑셀 원본 저장
    output_folder_id: str = ""  # 생성된 PPT / 분석결과 저장

    # --- 로컬 폴백 경로 (Dataiku 밖에서 실행 시) ---
    local_input_dir: str = "./data/input"
    local_output_dir: str = "./data/output"

    # 분석 시 LLM 프롬프트에 넣을 초록 샘플 최대 개수
    abstract_sample_size: int = 40

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            openai_api_key=_get("OPENAI_API_KEY", ""),
            openai_model=_get("OPENAI_MODEL", "gpt-4o"),
            openai_temperature=float(_get("OPENAI_TEMPERATURE", "0.3")),
            openai_max_tokens=int(_get("OPENAI_MAX_TOKENS", "1800")),
            input_folder_id=_get("DKU_INPUT_FOLDER_ID", ""),
            output_folder_id=_get("DKU_OUTPUT_FOLDER_ID", ""),
            local_input_dir=_get("LOCAL_INPUT_DIR", "./data/input"),
            local_output_dir=_get("LOCAL_OUTPUT_DIR", "./data/output"),
            abstract_sample_size=int(_get("ABSTRACT_SAMPLE_SIZE", "40")),
        )


settings = Settings.load()
