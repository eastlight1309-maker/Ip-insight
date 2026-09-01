/* ==========================================================================
   Dataiku "Standard(코드) 웹앱"의 [JS] 탭에 붙여넣을 코드.
   백엔드(webbackend.py)의 /api/* 엔드포인트를 호출해 UI를 구동합니다.
========================================================================== */
(function () {
  "use strict";

  // Dataiku 가 제공하는 백엔드 URL 헬퍼. (로컬 테스트 시 상대경로로 폴백)
  function api(path) {
    try {
      if (typeof getWebAppBackendUrl === "function") return getWebAppBackendUrl(path);
    } catch (e) {}
    return path;
  }

  var $ = function (id) { return document.getElementById(id); };

  var state = {
    token: null,
    filename: null,
    columns: [],
    langsLoaded: false,
    lastResult: null, // { project, output_filename }
  };

  // ---- 유틸 ----
  function setStatus(el, msg, cls) {
    el.className = "status" + (cls ? " " + cls : "");
    el.textContent = msg || "";
  }

  function fillSelect(sel, items, valueKey, labelKey, selectedVal) {
    sel.innerHTML = "";
    items.forEach(function (it) {
      var opt = document.createElement("option");
      opt.value = valueKey ? it[valueKey] : it;
      opt.textContent = labelKey ? it[labelKey] : it;
      if (selectedVal != null && opt.value === selectedVal) opt.selected = true;
      sel.appendChild(opt);
    });
  }

  function downloadFile(url, filename) {
    // iframe 안에서도 안전하게 다운로드: blob 으로 받아 앵커 클릭
    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.blob();
      })
      .then(function (blob) {
        var a = document.createElement("a");
        var objUrl = URL.createObjectURL(blob);
        a.href = objUrl;
        a.download = filename || "download.xlsx";
        document.body.appendChild(a);
        a.click();
        setTimeout(function () {
          URL.revokeObjectURL(objUrl);
          document.body.removeChild(a);
        }, 1500);
      })
      .catch(function (e) { alert("다운로드 실패: " + e.message); });
  }

  function renderTable(table, columns, rows, newCols) {
    newCols = newCols || [];
    var thead = "<thead><tr>";
    columns.forEach(function (c) {
      var cls = newCols.indexOf(c) >= 0 ? ' class="newcol"' : "";
      thead += "<th" + cls + ">" + escapeHtml(c) + "</th>";
    });
    thead += "</tr></thead>";
    var tbody = "<tbody>";
    rows.forEach(function (r) {
      tbody += "<tr>";
      r.forEach(function (v, i) {
        var cls = newCols.indexOf(columns[i]) >= 0 ? ' class="newcol"' : "";
        tbody += "<td" + cls + ">" + escapeHtml(v) + "</td>";
      });
      tbody += "</tr>";
    });
    tbody += "</tbody>";
    table.innerHTML = thead + tbody;
  }

  function escapeHtml(s) {
    s = s == null ? "" : String(s);
    return s.replace(/[&<>"']/g, function (m) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[m];
    });
  }

  // ---- 탭 전환 ----
  function initTabs() {
    var btns = document.querySelectorAll(".tab-btn");
    btns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        btns.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        document.querySelectorAll(".tab-panel").forEach(function (p) { p.classList.remove("active"); });
        $(btn.getAttribute("data-tab")).classList.add("active");
        if (btn.getAttribute("data-tab") === "tab-history") loadProjects();
      });
    });
  }

  // ---- bootstrap: 드롭다운 채우기 ----
  function bootstrap() {
    fetch(api("/api/bootstrap"))
      .then(function (r) { return r.json(); })
      .then(function (b) {
        fillSelect($("llm"), b.llms, "id", "label", b.current_llm);
        fillSelect($("src"), b.languages.source, "code", "label", null);
        fillSelect($("tgt"), b.languages.target, "code", "label", "en");
        state.langsLoaded = true;

        var envTxt = b.env === "dataiku" ? "실행 환경: Dataiku LLM Mesh ✅" : "실행 환경: 로컬(폴백/데모)";
        $("env-line").textContent = envTxt + "  ·  입력폴더: " + b.input_location + "  ·  출력폴더: " + b.output_location;
        $("llm-note").textContent = b.llm_available
          ? "사용 LLM 준비됨"
          : "⚠️ 사용 가능한 LLM 없음 → 데모(자리표시자) 결과가 생성됩니다.";
      })
      .catch(function (e) {
        $("env-line").textContent = "백엔드 연결 실패: " + e.message + " — Python 백엔드가 활성화되어 있는지 확인하세요.";
      });
  }

  // ---- 파일 검사(inspect) ----
  function onFileChange() {
    var f = $("file").files[0];
    state.token = null;
    $("settings-card").style.display = "none";
    $("result-card").style.display = "none";
    if (!f) return;
    if (!$("project").value.trim()) {
      setStatus($("inspect-status"), "먼저 프로젝트 이름을 입력하세요.", "warn");
      return;
    }
    setStatus($("inspect-status"), "파일 분석 중…", "");
    var fd = new FormData();
    fd.append("file", f);
    fd.append("project", $("project").value.trim());
    fetch(api("/api/inspect"), { method: "POST", body: fd })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.j.error || "분석 실패");
        var j = res.j;
        state.token = j.token;
        state.filename = j.filename;
        // 시트
        if (j.sheets && j.sheets.length > 1) {
          $("sheet-row").style.display = "";
          fillSelect($("sheet"), j.sheets, null, null, j.sheet);
        } else {
          $("sheet-row").style.display = "none";
        }
        renderColumns(j.columns);
        $("settings-card").style.display = "";
        setStatus($("inspect-status"), "총 " + j.rows + "행 · " + j.columns.length + "컬럼 인식됨.", "ok");
      })
      .catch(function (e) { setStatus($("inspect-status"), e.message, "err"); });
  }

  function onSheetChange() {
    if (!state.token) return;
    var url = api("/api/columns") + "?token=" + encodeURIComponent(state.token) +
      "&sheet=" + encodeURIComponent($("sheet").value);
    fetch(url).then(function (r) { return r.json(); }).then(function (j) {
      if (j.columns) renderColumns(j.columns);
    });
  }

  function renderColumns(cols) {
    state.columns = cols || [];
    var box = $("columns");
    box.innerHTML = "";
    if (!state.columns.length) {
      box.innerHTML = '<span class="empty">컬럼이 없습니다.</span>';
    }
    state.columns.forEach(function (c, i) {
      var lbl = document.createElement("label");
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = c;
      cb.className = "col-cb";
      cb.addEventListener("change", updateRunEnabled);
      lbl.appendChild(cb);
      lbl.appendChild(document.createTextNode(" " + c));
      box.appendChild(lbl);
    });
    updateRunEnabled();
  }

  function selectedColumns() {
    return Array.prototype.slice.call(document.querySelectorAll(".col-cb"))
      .filter(function (cb) { return cb.checked; })
      .map(function (cb) { return cb.value; });
  }

  function updateRunEnabled() {
    var cols = selectedColumns();
    var same = $("src").value !== "auto" && $("src").value === $("tgt").value;
    $("run-btn").disabled = cols.length === 0 || same;
  }

  // ---- 번역 실행 ----
  function onRun() {
    var cols = selectedColumns();
    if (!cols.length) return;
    $("run-btn").disabled = true;
    setStatus($("progress"), "번역 중… (행/컬럼 수에 따라 시간이 걸립니다)", "");
    var payload = {
      token: state.token,
      project: $("project").value.trim(),
      columns: cols,
      src: $("src").value,
      tgt: $("tgt").value,
      llm_id: $("llm").value,
      sheet: $("sheet-row").style.display === "none" ? null : $("sheet").value,
      filename: state.filename,
    };
    fetch(api("/api/translate"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.j.error || "번역 실패");
        var t = res.j;
        state.lastResult = { project: t.project, output_filename: t.output_filename };
        var meta = "번역 완료 · " + t.row_count + "행 · 결과 저장: " + t.output_path;
        if (t.mode === "demo") meta += "  (⚠️ 데모 모드: [언어] 원문 자리표시자)";
        meta += "\n추가된 결과 컬럼: " + (t.new_columns.join(", ") || "없음");
        setStatus($("result-meta"), meta, t.mode === "demo" ? "warn" : "ok");
        renderTable($("result-table"), t.preview_columns, t.preview_rows, t.new_columns);
        $("result-card").style.display = "";
        setStatus($("progress"), "완료", "ok");
      })
      .catch(function (e) { setStatus($("progress"), e.message, "err"); })
      .then(function () { updateRunEnabled(); });
  }

  function onDownloadScreen() {
    if (!state.lastResult) return;
    var url = api("/api/download") + "?kind=output&project=" +
      encodeURIComponent(state.lastResult.project) + "&file=" +
      encodeURIComponent(state.lastResult.output_filename);
    downloadFile(url, state.lastResult.output_filename);
  }

  // ---- 히스토리(이전 결과) ----
  function loadProjects() {
    fetch(api("/api/bootstrap")).then(function (r) { return r.json(); }).then(function (b) {
      var cur = $("hist-project").value;
      fillSelect($("hist-project"), b.projects || [], null, null, cur || null);
      if ((b.projects || []).length) loadHistory();
      else {
        $("hist-file").innerHTML = "";
        setStatus($("hist-status"), "아직 저장된 번역 결과가 없습니다.", "");
      }
    });
  }

  function loadHistory() {
    var proj = $("hist-project").value;
    if (!proj) return;
    setStatus($("hist-status"), "", "");
    var url = api("/api/history") + "?project=" + encodeURIComponent(proj);
    fetch(url).then(function (r) { return r.json(); }).then(function (h) {
      fillSelect($("hist-file"), h.files || [], null, null, null);
      fillSelect($("hist-input-file"), h.input_files || [], null, null, null);
      $("hist-location").textContent = "저장 위치: " + (h.location || "");
      if (!(h.files || []).length) setStatus($("hist-status"), "이 프로젝트에 저장된 결과 파일이 없습니다.", "");
    });
  }

  function onHistPreview() {
    var proj = $("hist-project").value, file = $("hist-file").value;
    if (!proj || !file) return;
    setStatus($("hist-status"), "미리보기 불러오는 중…", "");
    var url = api("/api/preview") + "?kind=output&project=" +
      encodeURIComponent(proj) + "&file=" + encodeURIComponent(file);
    fetch(url).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.j.error || "미리보기 실패");
        renderTable($("hist-table"), res.j.columns, res.j.rows, []);
        setStatus($("hist-status"), "", "");
      })
      .catch(function (e) { setStatus($("hist-status"), e.message, "err"); });
  }

  function onHistDownload() {
    var proj = $("hist-project").value, file = $("hist-file").value;
    if (!proj || !file) return;
    var url = api("/api/download") + "?kind=output&project=" +
      encodeURIComponent(proj) + "&file=" + encodeURIComponent(file);
    downloadFile(url, file);
  }

  function onHistInputDownload() {
    var proj = $("hist-project").value, file = $("hist-input-file").value;
    if (!proj || !file) return;
    var url = api("/api/download") + "?kind=input&project=" +
      encodeURIComponent(proj) + "&file=" + encodeURIComponent(file);
    downloadFile(url, file);
  }

  // ---- 초기화 ----
  function init() {
    initTabs();
    bootstrap();
    $("file").addEventListener("change", onFileChange);
    $("project").addEventListener("change", function () {
      if ($("file").files[0]) onFileChange();
    });
    $("sheet").addEventListener("change", onSheetChange);
    $("src").addEventListener("change", updateRunEnabled);
    $("tgt").addEventListener("change", updateRunEnabled);
    $("run-btn").addEventListener("click", onRun);
    $("download-screen").addEventListener("click", onDownloadScreen);
    $("hist-project").addEventListener("change", loadHistory);
    $("hist-refresh").addEventListener("click", loadProjects);
    $("hist-preview").addEventListener("click", onHistPreview);
    $("hist-download").addEventListener("click", onHistDownload);
    $("hist-input-download").addEventListener("click", onHistInputDownload);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
