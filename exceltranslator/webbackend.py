"""Dataiku **Standard(코드) 웹앱** 용 Flask 백엔드.

Streamlit 이 아니라 Dataiku 표준 웹앱(HTML/JS 프론트 + Python 백엔드)에서
사용한다. Python 백엔드 탭에는 아래 2줄만 넣으면 된다:

    from exceltranslator.webbackend import register_routes
    register_routes(app)          # `app` 은 Dataiku 가 제공하는 Flask 앱

모든 실제 로직은 기존 `exceltranslator` 패키지(service/dataiku_io/llm/…)를
그대로 재사용한다. 프론트엔드(webapp.js)는 아래 JSON 엔드포인트만 호출한다:

  GET  /api/bootstrap                 → LLM/언어/환경/프로젝트 목록 (드롭다운 채우기)
  POST /api/inspect   (multipart)     → 업로드 파일 검사 → 시트/컬럼 반환(+토큰)
  GET  /api/columns?token=&sheet=     → 특정 시트의 컬럼 목록
  POST /api/translate (json)          → 번역 실행 → 저장 + 미리보기 반환
  GET  /api/history?project=          → 프로젝트별 결과/입력 파일 목록
  GET  /api/download?kind=&project=&file=  → 파일 다운로드(스트리밍)
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Dict

from flask import Response, jsonify, request

from . import dataiku_io, excel_io, llm, service
from .config import (
    ALLOWED_LLM_CANDIDATES,
    AUTO_DETECT,
    LANGUAGES,
    language_label,
    settings,
)

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# 업로드 임시 캐시 (token -> bytes). 표준 웹앱 백엔드는 단일 프로세스라고 가정.
_UPLOAD_CACHE: Dict[str, bytes] = {}
_CACHE_LIMIT = 8


def _remember(data: bytes) -> str:
    """업로드 바이트를 토큰으로 캐시. 용량 초과 시 가장 오래된 항목 제거."""
    token = uuid.uuid4().hex
    while len(_UPLOAD_CACHE) >= _CACHE_LIMIT:
        oldest = next(iter(_UPLOAD_CACHE))
        _UPLOAD_CACHE.pop(oldest, None)
    _UPLOAD_CACHE[token] = data
    return token


def _clean(v) -> str:
    """미리보기 셀 값을 문자열로 정리(NaN/None → 빈 문자열)."""
    if v is None:
        return ""
    try:
        if isinstance(v, float) and math.isnan(v):
            return ""
    except Exception:
        pass
    return str(v)


def _lang_options():
    src = [{"code": AUTO_DETECT, "label": language_label(AUTO_DETECT)}]
    src += [{"code": c, "label": language_label(c)} for c in LANGUAGES]
    tgt = [{"code": c, "label": language_label(c)} for c in LANGUAGES]
    return {"source": src, "target": tgt}


def register_routes(app) -> None:
    """Dataiku 가 제공하는 Flask `app` 에 API 라우트를 등록한다."""

    @app.route("/api/bootstrap", methods=["GET"])
    def bootstrap():  # noqa: D401
        return jsonify(
            {
                "env": "dataiku" if llm.is_dataiku() else "local",
                "llms": [{"id": i, "label": l} for l, i in ALLOWED_LLM_CANDIDATES],
                "current_llm": settings.llm_id,
                "llm_available": llm.get_client() is not None,
                "languages": _lang_options(),
                "input_location": dataiku_io.location_hint("input"),
                "output_location": dataiku_io.location_hint("output"),
                "projects": dataiku_io.list_projects("output"),
            }
        )

    @app.route("/api/inspect", methods=["POST"])
    def inspect():
        f = request.files.get("file")
        if f is None:
            return jsonify({"error": "파일이 없습니다."}), 400
        data = f.read()
        if not data:
            return jsonify({"error": "빈 파일입니다."}), 400
        try:
            sheets = excel_io.sheet_names(data)
            first = sheets[0] if sheets else 0
            df = excel_io.read_excel(data, first)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"엑셀을 읽지 못했습니다: {exc}"}), 400
        token = _remember(data)
        return jsonify(
            {
                "token": token,
                "filename": f.filename,
                "sheets": sheets,
                "sheet": first if isinstance(first, str) else "",
                "columns": [str(c) for c in df.columns],
                "rows": int(len(df)),
            }
        )

    @app.route("/api/columns", methods=["GET"])
    def columns():
        token = request.args.get("token", "")
        sheet = request.args.get("sheet", "")
        data = _UPLOAD_CACHE.get(token)
        if data is None:
            return jsonify({"error": "업로드 세션이 만료되었습니다. 파일을 다시 업로드하세요."}), 400
        try:
            df = excel_io.read_excel(data, sheet or 0)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": str(exc)}), 400
        return jsonify({"columns": [str(c) for c in df.columns], "rows": int(len(df))})

    @app.route("/api/translate", methods=["POST"])
    def translate():
        body = request.get_json(force=True, silent=True) or {}
        token = body.get("token", "")
        project = (body.get("project") or "").strip()
        cols = body.get("columns") or []
        src = body.get("src") or AUTO_DETECT
        tgt = body.get("tgt") or "en"
        llm_id = body.get("llm_id")
        sheet = body.get("sheet") or None
        filename = body.get("filename") or "upload.xlsx"

        if not project:
            return jsonify({"error": "프로젝트 이름을 입력하세요."}), 400
        if not cols:
            return jsonify({"error": "번역할 컬럼을 선택하세요."}), 400
        if src != AUTO_DETECT and src == tgt:
            return jsonify({"error": "출발 언어와 도착 언어가 같습니다."}), 400
        data = _UPLOAD_CACHE.get(token)
        if data is None:
            return jsonify({"error": "업로드 세션이 만료되었습니다. 파일을 다시 업로드하세요."}), 400

        if llm_id:
            settings.set_llm_id(llm_id)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            out = service.run_translation(
                file_bytes=data,
                original_filename=filename,
                project=project,
                columns=cols,
                src_code=src,
                tgt_code=tgt,
                stamp=stamp,
                sheet_name=sheet,
            )
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"번역 실패: {exc}"}), 500

        prev = out.df.head(30)
        preview_rows = [[_clean(v) for v in r] for r in prev.values.tolist()]
        return jsonify(
            {
                "ok": True,
                "project": dataiku_io.safe_project(project),
                "output_filename": out.output_filename,
                "input_path": out.input_path,
                "output_path": out.output_path,
                "new_columns": out.new_columns,
                "translated_columns": out.translated_columns,
                "row_count": out.row_count,
                "mode": out.mode,
                "preview_columns": [str(c) for c in prev.columns],
                "preview_rows": preview_rows,
            }
        )

    @app.route("/api/history", methods=["GET"])
    def history():
        project = request.args.get("project", "")
        if not project:
            return jsonify({"files": [], "input_files": [], "location": ""})
        return jsonify(
            {
                "files": dataiku_io.list_files("output", project),
                "input_files": dataiku_io.list_files("input", project),
                "location": dataiku_io.location_hint("output", project),
            }
        )

    @app.route("/api/preview", methods=["GET"])
    def preview():
        kind = request.args.get("kind", "output")
        project = request.args.get("project", "")
        fname = request.args.get("file", "")
        if kind not in ("input", "output") or not fname:
            return jsonify({"error": "잘못된 요청입니다."}), 400
        try:
            data = dataiku_io.read_bytes(kind, project, fname)
            df = excel_io.read_excel(data).head(30)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"미리보기 실패: {exc}"}), 404
        return jsonify(
            {
                "columns": [str(c) for c in df.columns],
                "rows": [[_clean(v) for v in r] for r in df.values.tolist()],
            }
        )

    @app.route("/api/download", methods=["GET"])
    def download():
        kind = request.args.get("kind", "output")
        project = request.args.get("project", "")
        fname = request.args.get("file", "")
        if kind not in ("input", "output") or not fname:
            return jsonify({"error": "잘못된 요청입니다."}), 400
        try:
            data = dataiku_io.read_bytes(kind, project, fname)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"파일을 찾을 수 없습니다: {exc}"}), 404
        # 파일명에 큰따옴표가 있으면 헤더가 깨질 수 있어 제거
        safe_name = str(fname).replace('"', "")
        return Response(
            data,
            mimetype=_XLSX_MIME,
            headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
        )
