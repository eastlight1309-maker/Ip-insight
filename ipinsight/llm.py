"""LLM 호출 추상화 계층.

우선순위:
  1) Dataiku LLM Mesh  — 허용된 LLM ID(project.get_llm)로 호출 (운영 기본 경로)
  2) OpenAI SDK        — 로컬 개발 시 OPENAI_API_KEY 가 있을 때만
  3) 데모(mock)        — 위 둘 다 불가할 때 자리표시자 반환

프론트/분석기는 `get_client()` 가 돌려주는 객체의 `.complete(system, user)` 만 쓴다.
"""

from __future__ import annotations

from typing import Optional, Protocol

from .config import ALLOWED_LLM_IDS, settings

try:  # Dataiku DSS 코드 환경에서만 존재
    import dataiku  # type: ignore

    _HAS_DATAIKU = True
except Exception:  # pragma: no cover
    dataiku = None  # type: ignore
    _HAS_DATAIKU = False


class LLMClient(Protocol):
    kind: str

    def complete(self, system: str, user: str) -> str:
        ...


# ---------------------------------------------------------------------------
# 1) Dataiku LLM Mesh
# ---------------------------------------------------------------------------
class DataikuLLMClient:
    kind = "dataiku"

    def __init__(self, llm_id: str):
        if llm_id not in ALLOWED_LLM_IDS:
            raise ValueError(f"허용되지 않은 LLM ID: {llm_id}")
        self.llm_id = llm_id
        client = dataiku.api_client()  # type: ignore
        project = client.get_default_project()
        self._llm = project.get_llm(llm_id)

    def complete(self, system: str, user: str) -> str:
        completion = self._llm.new_completion()
        completion.with_message(system, role="system")
        completion.with_message(user, role="user")
        # 설정(가능한 경우에만) — API 버전에 따라 없을 수 있어 방어적으로 처리
        try:
            completion.settings["temperature"] = settings.llm_temperature
            completion.settings["maxOutputTokens"] = settings.llm_max_tokens
        except Exception:
            pass
        resp = completion.execute()
        if not getattr(resp, "success", False):
            raise RuntimeError(f"Dataiku LLM 호출 실패: {getattr(resp, 'text', 'unknown error')}")
        return resp.text or ""


# ---------------------------------------------------------------------------
# 2) OpenAI SDK (로컬 개발 폴백)
# ---------------------------------------------------------------------------
class OpenAIClient:
    kind = "openai"

    def __init__(self):
        from openai import OpenAI  # openai>=1.0

        self._client = OpenAI(api_key=settings.openai_api_key)

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=settings.openai_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# 팩토리
# ---------------------------------------------------------------------------
def is_dataiku() -> bool:
    return _HAS_DATAIKU


def get_client() -> Optional[LLMClient]:
    """사용 가능한 LLM 클라이언트를 반환. 없으면 None(데모 모드)."""
    if _HAS_DATAIKU:
        try:
            return DataikuLLMClient(settings.llm_id)
        except Exception:
            # Dataiku 환경이지만 LLM 접근 실패 시 폴백 시도로 넘어감
            pass
    if settings.openai_api_key:
        try:
            return OpenAIClient()
        except Exception:
            return None
    return None
