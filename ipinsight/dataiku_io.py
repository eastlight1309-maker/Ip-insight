"""Dataiku 관리 폴더(Managed Folder) 입출력 계층.

Dataiku 안에서 실행되면 `dataiku.Folder` API로 저장/조회하고,
로컬(개발/테스트)에서 실행되면 파일시스템으로 자동 폴백한다.
프론트엔드는 이 모듈만 호출하면 되고, 실행 환경을 몰라도 된다.
"""

from __future__ import annotations

import os
from typing import List, Optional

from .config import settings

try:  # Dataiku DSS 코드 환경에서만 존재
    import dataiku  # type: ignore

    _HAS_DATAIKU = True
except Exception:  # pragma: no cover - 로컬 환경
    dataiku = None  # type: ignore
    _HAS_DATAIKU = False


def is_dataiku() -> bool:
    """Dataiku 환경 여부."""
    return _HAS_DATAIKU


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------
def _local_dir(kind: str) -> str:
    path = settings.local_input_dir if kind == "input" else settings.local_output_dir
    os.makedirs(path, exist_ok=True)
    return path


def _folder_ref(kind: str) -> str:
    return settings.input_folder_ref if kind == "input" else settings.output_folder_ref


def _folder(kind: str):
    """kind: 'input' | 'output' 에 해당하는 Dataiku Folder 핸들 반환.

    dataiku.Folder(ref) 는 폴더 '이름' 또는 'ID' 모두 허용한다.
    """
    ref = _folder_ref(kind)
    if not ref:
        raise RuntimeError(
            f"Dataiku {kind} 폴더가 설정되지 않았습니다. "
            f"환경변수 DKU_{kind.upper()}_FOLDER (이름) 또는 DKU_{kind.upper()}_FOLDER_ID 를 지정하세요."
        )
    return dataiku.Folder(ref)  # type: ignore


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------
def save_bytes(kind: str, filename: str, data: bytes) -> str:
    """바이트 데이터를 input/output 폴더에 저장하고 저장 경로(식별자)를 반환."""
    if is_dataiku():
        folder = _folder(kind)
        with folder.get_writer(filename) as w:
            w.write(data)
        return filename
    path = os.path.join(_local_dir(kind), filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def read_bytes(kind: str, filename: str) -> bytes:
    """저장된 파일을 바이트로 읽는다."""
    if is_dataiku():
        folder = _folder(kind)
        with folder.get_download_stream(filename) as s:
            return s.read()
    path = os.path.join(_local_dir(kind), filename)
    with open(path, "rb") as f:
        return f.read()


def list_files(kind: str) -> List[str]:
    """폴더 내 파일 목록."""
    if is_dataiku():
        folder = _folder(kind)
        return [p.lstrip("/") for p in folder.list_paths_in_partition()]
    d = _local_dir(kind)
    return sorted(os.listdir(d))


def location_hint(kind: str) -> str:
    """UI 표시에 쓰는, 파일이 저장되는 위치 설명."""
    if is_dataiku():
        return f"Dataiku 관리 폴더 '{_folder_ref(kind)}'"
    return os.path.abspath(_local_dir(kind))
