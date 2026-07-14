"""LLM 기반 번역 엔진.

- LLM 클라이언트(llm.get_client)의 `.complete(system, user)` 만 사용한다.
- 여러 셀을 한 번의 호출로 묶어(batch) 번역해 호출 수를 줄인다.
- LLM 응답은 JSON 매핑으로 요청하고, 파싱 실패 시 방어적으로 폴백한다.
- 클라이언트가 없으면(데모 모드) 원문 앞에 [목표언어] 표식을 붙여 파이프라인을 검증한다.
"""

from __future__ import annotations

import json
import re
from typing import Callable, List, Optional

from .config import language_english_name, settings
from .llm import LLMClient

_SYSTEM_PROMPT = (
    "You are a professional translator. Translate each numbered text item from "
    "{src} into {tgt}. Preserve meaning, tone, numbers, product names, and any "
    "inline formatting. Do NOT add explanations. Return ONLY a JSON object whose "
    "keys are the item numbers (as strings) and whose values are the translated "
    "strings. Example: {{\"1\": \"...\", \"2\": \"...\"}}."
)


def _demo_translate(texts: List[str], tgt_code: str) -> List[str]:
    tag = tgt_code.upper()
    out = []
    for t in texts:
        if t is None or str(t).strip() == "":
            out.append(t)
        else:
            out.append(f"[{tag}] {t}")
    return out


def _extract_json_obj(raw: str) -> Optional[dict]:
    """LLM 응답 문자열에서 JSON 오브젝트를 최대한 견고하게 추출."""
    if not raw:
        return None
    text = raw.strip()
    # ```json ... ``` 코드펜스 제거
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    # 그대로 파싱 시도
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # 첫 '{' ~ 마지막 '}' 사이만 잘라 재시도
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return None


def _translate_batch(
    client: LLMClient, texts: List[str], src_code: str, tgt_code: str
) -> List[str]:
    """비어있지 않은 텍스트 배치 하나를 번역한다."""
    system = _SYSTEM_PROMPT.format(
        src=language_english_name(src_code), tgt=language_english_name(tgt_code)
    )
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    user = "Translate the following items:\n\n" + numbered

    try:
        raw = client.complete(system, user)
    except Exception:
        # 호출 실패 시 원문 유지 (파이프라인 중단 방지)
        return list(texts)

    obj = _extract_json_obj(raw)
    if obj is None:
        # JSON 파싱 실패: 원문 유지
        return list(texts)

    result: List[str] = []
    for i, original in enumerate(texts):
        key = str(i + 1)
        val = obj.get(key)
        if val is None:
            # 정수 키로 저장됐을 가능성도 확인
            val = obj.get(i + 1)
        result.append(str(val) if val is not None else original)
    return result


def translate_texts(
    client: Optional[LLMClient],
    texts: List[str],
    src_code: str,
    tgt_code: str,
    batch_size: Optional[int] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> List[str]:
    """문자열 리스트를 번역해 같은 길이의 리스트로 반환.

    - 빈 문자열/None 은 번역하지 않고 그대로 둔다.
    - client 가 None 이면 데모 모드.
    - progress(done, total) 콜백으로 진행률을 보고할 수 있다.
    """
    n = len(texts)
    if n == 0:
        return []

    if client is None:
        if progress:
            progress(n, n)
        return _demo_translate(texts, tgt_code)

    bs = batch_size or settings.batch_size

    # 번역 대상(비어있지 않은) 인덱스만 추린다.
    todo_idx = [i for i, t in enumerate(texts) if t is not None and str(t).strip() != ""]
    out: List[str] = list(texts)  # 기본값: 원문 유지

    total = len(todo_idx)
    done = 0
    for start in range(0, total, bs):
        chunk_idx = todo_idx[start : start + bs]
        chunk_txt = [str(texts[i]) for i in chunk_idx]
        translated = _translate_batch(client, chunk_txt, src_code, tgt_code)
        for j, i in enumerate(chunk_idx):
            if j < len(translated):
                out[i] = translated[j]
        done += len(chunk_idx)
        if progress:
            progress(done, total)

    if progress and total == 0:
        progress(n, n)
    return out
