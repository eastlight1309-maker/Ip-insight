"""Dataiku 관리 폴더(Managed Folder) 입출력 계층 — 프로젝트별 하위 폴더 지원.

Dataiku 안에서 실행되면 `dataiku.Folder` API로 저장/조회하고,
로컬(개발/테스트)에서 실행되면 파일시스템으로 자동 폴백한다.

파일은 프로젝트 이름을 하위 경로로 하여 저장한다:
    <input_folder>/<project>/<filename>
    <output_folder>/<project>/<filename>
이렇게 하면 한 관리 폴더 안에서 프로젝트별로 입력/출력이 구분된다.
"""

from __future__ import annotations

import os
import re
from typing import List

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
# 프로젝트 이름 정규화
# ---------------------------------------------------------------------------
_SAFE_RE = re.compile(r"[^0-9A-Za-z가-힣_\-]+")


def safe_project(name: str) -> str:
    """프로젝트 이름을 안전한 경로 조각으로 정규화. 비면 'default'."""
    name = (name or "").strip()
    cleaned = _SAFE_RE.sub("_", name).strip("_")
    return cleaned or "default"


def _rel_path(project: str, filename: str) -> str:
    """관리 폴더 내부의 상대 경로(POSIX 스타일)."""
    return f"{safe_project(project)}/{filename}"


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------
def _local_base(kind: str) -> str:
    return settings.local_input_dir if kind == "input" else settings.local_output_dir


def _local_path(kind: str, project: str, filename: str) -> str:
    path = os.path.join(_local_base(kind), safe_project(project), filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
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
            f"환경변수 DKU_TRANSLATOR_{kind.upper()}_FOLDER (이름) 또는 "
            f"DKU_TRANSLATOR_{kind.upper()}_FOLDER_ID 를 지정하세요."
        )
    return dataiku.Folder(ref)  # type: ignore


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------
def save_bytes(kind: str, project: str, filename: str, data: bytes) -> str:
    """바이트 데이터를 input/output 폴더의 <project>/ 하위에 저장하고 경로를 반환."""
    rel = _rel_path(project, filename)
    if is_dataiku():
        folder = _folder(kind)
        with folder.get_writer(rel) as w:
            w.write(data)
        return rel
    path = _local_path(kind, project, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def read_bytes(kind: str, project: str, filename: str) -> bytes:
    """저장된 파일을 바이트로 읽는다. (project + filename 또는 이미 완성된 상대경로)"""
    if is_dataiku():
        folder = _folder(kind)
        # filename 이 이미 <project>/name 형태면 그대로, 아니면 조합
        rel = filename if "/" in filename else _rel_path(project, filename)
        with folder.get_download_stream(rel) as s:
            return s.read()
    if os.path.isabs(filename) or filename.startswith("."):
        path = filename
    else:
        path = _local_path(kind, project, os.path.basename(filename))
    with open(path, "rb") as f:
        return f.read()


def list_files(kind: str, project: str) -> List[str]:
    """특정 프로젝트의 파일 목록(파일명만)을 최신순 비슷하게 정렬해 반환."""
    prefix = safe_project(project) + "/"
    if is_dataiku():
        folder = _folder(kind)
        names = []
        for p in folder.list_paths_in_partition():
            p = p.lstrip("/")
            if p.startswith(prefix):
                names.append(p[len(prefix):])
        return sorted(names, reverse=True)
    d = os.path.join(_local_base(kind), safe_project(project))
    if not os.path.isdir(d):
        return []
    return sorted(os.listdir(d), reverse=True)


def list_projects(kind: str) -> List[str]:
    """관리 폴더 안에 존재하는 프로젝트(하위 폴더) 목록을 반환."""
    projects = set()
    if is_dataiku():
        folder = _folder(kind)
        for p in folder.list_paths_in_partition():
            p = p.lstrip("/")
            if "/" in p:
                projects.add(p.split("/", 1)[0])
    else:
        base = _local_base(kind)
        if os.path.isdir(base):
            for name in os.listdir(base):
                if os.path.isdir(os.path.join(base, name)):
                    projects.add(name)
    return sorted(projects)


def location_hint(kind: str, project: str = "") -> str:
    """UI 표시에 쓰는, 파일이 저장되는 위치 설명."""
    suffix = f"/{safe_project(project)}" if project else ""
    if is_dataiku():
        return f"Dataiku 관리 폴더 '{_folder_ref(kind)}'{suffix}"
    base = os.path.abspath(_local_base(kind))
    return base + (os.sep + safe_project(project) if project else "")
