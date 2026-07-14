# 📊 IP Insight 분석기

Derwent **DWPI**를 포함한 특허 엑셀 파일을 업로드하면, **Dataiku LLM Mesh**로 연결된
허용 LLM(GPT‑5.x)으로 다양한 IP 인사이트를 도출하고 **PowerPoint 리포트**로 내려받는
웹앱입니다. **Dataiku DSS의 Streamlit 웹앱**으로 배포하는 것을 전제로 설계했으며,
입력 엑셀과 출력 PPT는 **Dataiku 관리 폴더(Managed Folder)**에 저장됩니다.

---

## 1. 구조 (백엔드 / 프론트엔드 분리)

```
Ip-insight/
├── frontend/
│   └── app.py              # 로컬 실행 진입점(얇은 래퍼) — ipinsight.webapp.main 호출
├── ipinsight/              # 순수 로직 + UI 패키지 (Dataiku 프로젝트 라이브러리에 배치)
│   ├── webapp.py           # Streamlit UI (업로드·매핑·선택·결과·다운로드)
│   ├── insights.py         # 인사이트 카탈로그 + 추천 항목 정의  ★
│   ├── config.py           # 환경변수/설정 (+ 허용 LLM 목록)
│   ├── dataiku_io.py       # Dataiku 관리 폴더 I/O (+ 로컬 폴백)
│   ├── data_loader.py      # 엑셀 로드 + DWPI 컬럼 정규화
│   ├── analytics.py        # 정량 통계 (LLM 컨텍스트 + 차트용)
│   ├── llm.py              # LLM 호출 추상화 (Dataiku LLM Mesh → OpenAI 폴백 → 데모)
│   ├── llm_analyzer.py     # 인사이트별 분석 생성
│   ├── ppt_builder.py      # python-pptx 리포트 생성 (네이티브 차트)
│   └── service.py          # 파이프라인 오케스트레이션 (진입점)
├── dataiku_webapp_code.py  # Dataiku 웹앱 편집기에 붙여넣을 2줄 코드
├── scripts/make_sample.py  # 데모용 가상 DWPI 엑셀 생성
├── tests/test_pipeline.py  # 엔드투엔드 스모크 테스트
├── sample/                 # 샘플 엑셀
└── requirements.txt
```

> **⚠️ 패키지 이름을 `backend`로 쓰지 않는 이유:** Dataiku 웹앱은 백엔드 코드를
> 실행 폴더 `backend/main.py` 에 배치합니다. 공용 패키지를 `backend`로 두면
> `from backend import ...` 가 이 실행 폴더와 충돌해
> `ImportError: cannot import name '...' from 'backend' (unknown location)` 이 납니다.
> 그래서 패키지명을 **`ipinsight`** 로 두고, Dataiku에서는 이를 **프로젝트 라이브러리**에
> 넣어 임포트합니다(§4 참고).

**데이터 흐름:** 엑셀 업로드 → (입력 폴더 저장) → 정규화 → 정량 통계 →
LLM 인사이트 분석 → PPT 생성 → (출력 폴더 저장) → 다운로드.

---

## 2. 인사이트별 추천 항목 (요청하신 "무엇을 담으면 좋은지")

`ipinsight/insights.py`에 코드로도 정의되어 있으며, UI에서 각 인사이트의
"추천 항목 보기"로도 확인할 수 있습니다.

| # | 인사이트 | 포함하면 좋은 항목 |
|---|----------|--------------------|
| 1 | **기술 트렌드 분석** | 연도별 출원 추이 · 급성장/급감 영역 · 최근 부상(Emerging) 기술 · 기술 성숙도 단계 · 향후 3~5년 전망 |
| 2 | **주요 출원인/경쟁사** | 상위 출원인 Top10·점유율 · 출원인별 집중 영역 · 신규 진입자 · 공동출원 관계 · 경쟁 강도 |
| 3 | **기술 분류(Landscape)** | 상위 IPC/CPC · DWPI Class/Manual Code 분포 · 분류 융합 패턴 · 핵심 vs 주변 기술 · 지형도 요약 |
| 4 | **핵심 기술 테마/클러스터** | 기술 클러스터 5~8개 · 대표 특허 · 해결 과제(Novelty) · 기술 효과(Advantage/Use) · 테마 간 연관성 |
| 5 | **공백 기술/기회** | 미개척 영역 · 저경쟁·고성장 영역 · 확보 가능 포지션 · 진입 리스크 · 우선 검토 권고 |
| 6 | **발명자/R&D 역량** | 핵심 발명자 Top10 · 발명자–출원인 매핑/팀 구조 · R&D 생산성 · 전문 영역 · 인재 시사점 |
| 7 | **지역/시장(패밀리)** | 국가별 출원 분포 · 주요 타겟 시장 · 패밀리 확장 전략 · 지역별 경쟁 강도 · 진입 우선순위 |
| 8 | **인용/영향력** | 피인용 상위 특허 · 허브(영향력) 특허 · 기술 흐름 · 출원인별 영향력 · 라이선싱/회피 시사점 |
| 9 | **포트폴리오 강점/리스크** | 강점 영역 · 취약/리스크 영역 · 경쟁사 대비 포지션 · 라이선싱/M&A 시사점 · 강화 전략 |
| 10 | **종합 요약(Executive)** | 핵심 발견 3~5 · 전략적 시사점 · 즉시 실행 권고 · 중장기 과제 · 핵심 리스크/대응 |

---

## 3. 지원하는 엑셀 컬럼 (DWPI 자동 인식)

컬럼명은 버전/설정마다 다를 수 있어 **동의어를 자동 매핑**합니다
(`ipinsight/data_loader.py`). 대표 정규 컬럼:

`publication_number, title, abstract, dwpi_title, dwpi_abstract, assignee,
dwpi_assignee, inventor, priority_date, application_date, publication_date,
ipc, cpc, dwpi_class, dwpi_manual_code, country, family_id,
cited_refs, citing_patents`

여러 값이 한 셀에 있는 경우(`;`, `|`, `,`, `//` 구분)도 분해해 집계합니다.

### 매핑 확인 및 수동 지정
업로드 시 위 정규 컬럼으로 **자동 매핑**되며, 화면의 *"미리보기 & 컬럼 매핑"* 에서
결과를 표로 확인할 수 있습니다. **"수동으로 매핑 수정하기"** 를 켜면 각 정규 항목마다
엑셀 원본 컬럼을 드롭다운으로 직접 지정할 수 있습니다(자동 인식 실패/오인식 보정).
한 원본 컬럼을 여러 정규 항목에 중복 지정하면 경고가 표시됩니다.

---

## 4. Dataiku 배포 가이드

1. **관리 폴더 2개 생성** (Flow → +Dataset/Folder): 입력용/출력용.
   기본 폴더명은 아래와 같으며(원하면 변경 가능), 폴더는 **이름 또는 ID** 로 지정할 수 있습니다.

   | 용도 | 기본 폴더명 | 저장되는 파일명 |
   |------|-------------|-----------------|
   | 입력(업로드 엑셀) | `ip_insight_input` | `input_patents_<타임스탬프>.xlsx` |
   | 출력(PPT 리포트) | `ip_insight_output` | `ip_insight_report_<타임스탬프>.pptx` |

   폴더명을 바꾸려면 환경변수 `DKU_INPUT_FOLDER` / `DKU_OUTPUT_FOLDER`(이름) 또는
   `DKU_INPUT_FOLDER_ID` / `DKU_OUTPUT_FOLDER_ID`(ID)를 지정하세요.
2. **코드 환경**: `requirements.txt`의 패키지를 포함한 Python 코드 환경 생성
   (`dataiku`는 기본 제공되므로 별도 설치 불필요).
3. **공용 로직을 프로젝트 라이브러리에 등록** (중요 — ImportError 예방):
   - 프로젝트 상단 `</> (Code)` → **Libraries** 편집기로 이동.
   - `python/` 아래에 **`ipinsight/` 폴더 전체**(이 저장소의 `ipinsight/*.py`)를 복사해 넣습니다.
     결과 경로 예: `python/ipinsight/service.py`, `python/ipinsight/__init__.py` …
   - 프로젝트 라이브러리의 `python/` 는 웹앱 백엔드의 `sys.path` 에 자동 포함되어
     `from ipinsight import ...` 가 동작합니다. (Git 연동 프로젝트라면 커밋만으로 반영)
4. **웹앱 생성**: *Code* → *Webapps* → **Code webapp** → **Streamlit** 선택.
   - 웹앱 Python 코드에는 **아래 2줄만** 넣습니다(= `dataiku_webapp_code.py` 내용):
     ```python
     from ipinsight.webapp import main
     main()
     ```
   - 실제 UI 는 `ipinsight/webapp.py`(라이브러리)에 있으므로, 이후 UI를 수정해도
     웹앱 편집기 코드는 그대로 두면 됩니다. 라이브러리만 갱신하면 반영됩니다.
   - 웹앱 설정에서 3단계의 코드 환경을 지정.
   - ⚠️ **이전에 `from backend import ...` 코드를 붙여넣었다면 반드시 위 2줄로 교체**하세요.
     Git push는 DSS 웹앱 편집기 코드를 자동으로 바꾸지 않습니다.
5. **LLM 연결(LLM Mesh)**: DSS 관리자가 아래 허용된 LLM 연결을 활성화해야 합니다.
   앱은 `project.get_llm(<LLM_ID>)` 로 호출하며, 별도 API 키를 코드에 넣지 않습니다.

| 표시명 | LLM Mesh ID |
|--------|-------------|
| gpt-5.3-chat | `azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.3-chat` |
| gpt-5.4-nano | `azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4-nano` |
| gpt-5.4-mini | `azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4-mini` |
| gpt-5.4 | `azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4` |

   목록은 `ipinsight/config.py`의 `ALLOWED_LLM_CANDIDATES`에서 관리하며, UI 사이드바에서
   이 중 하나를 선택합니다.

6. **환경변수/시크릿 설정** (아래 표):

| 환경변수 | 설명 | 예시 |
|----------|------|------|
| `DKU_LLM_ID` | 기본 LLM Mesh ID (허용 목록 중 하나) | `azureopenai:dw-aoai-chat-eastus2-cognitiv:gpt-5.4` |
| `DKU_INPUT_FOLDER` | 입력 관리 폴더 **이름** (기본 `ip_insight_input`) | `ip_insight_input` |
| `DKU_OUTPUT_FOLDER` | 출력 관리 폴더 **이름** (기본 `ip_insight_output`) | `ip_insight_output` |
| `DKU_INPUT_FOLDER_ID` / `DKU_OUTPUT_FOLDER_ID` | (대안) 폴더를 ID로 지정 | `AbC12xYz` |
| `LLM_TEMPERATURE` / `LLM_MAX_TOKENS` | (선택) 생성 파라미터 | `0.3` / `1800` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | (선택) **로컬 개발 폴백 전용** | `sk-...` / `gpt-4o` |

> 운영(Dataiku)에서는 LLM Mesh를 통해 인증되므로 `OPENAI_API_KEY`가 필요 없습니다.
> `OPENAI_*`는 Dataiku 밖 로컬 개발에서만 폴백으로 사용됩니다.

배포되면 업로드된 엑셀은 입력 폴더에, 생성된 PPT는 출력 폴더에 자동 저장되고,
사용자는 웹앱에서 PPT를 바로 다운로드합니다.

---

## 5. 로컬 실행 (개발/테스트)

Dataiku 밖에서는 관리 폴더 대신 `data/input`, `data/output` 로 자동 폴백합니다.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/make_sample.py            # 샘플 엑셀 생성
export OPENAI_API_KEY=sk-...             # (선택) 없으면 데모 모드
streamlit run frontend/app.py
```

**테스트:**
```bash
python tests/test_pipeline.py            # API 키 없이 데모 모드 스모크 테스트
```

---

## 6. LLM 동작 모드 (우선순위)

1. **Dataiku LLM Mesh** (운영 기본): 허용된 LLM ID로 `project.get_llm(...)` 호출.
   각 인사이트마다 정량 통계 + DWPI 초록 샘플을 컨텍스트로 전달, 추천 항목을
   채운 구조화(JSON) 분석을 생성.
2. **OpenAI 폴백** (로컬 개발): Dataiku가 없고 `OPENAI_API_KEY`가 있을 때만.
3. **데모(mock)**: 위 둘 다 불가할 때 자리표시자 결과로 파이프라인/PPT 검증.
