# 📈 IP_Landscape chart

특허 데이터를 업로드하면 **IP 랜드스케이프 차트**를 생성·시각화하는 웹앱입니다.
Streamlit 기반이며, 로컬 실행과 Dataiku DSS 웹앱 배포를 모두 지원하는 구조로
설계되어 있습니다.

---

## 1. 프로젝트 구조

```
ip-landscape-chart/
├── frontend/
│   └── app.py              # 로컬 실행 진입점(얇은 래퍼) — iplandscape.webapp.main 호출
├── iplandscape/            # 앱 패키지 (로직 + UI)
│   ├── __init__.py
│   ├── config.py           # 환경변수/설정
│   └── webapp.py           # Streamlit UI
├── dataiku_webapp_code.py  # Dataiku 웹앱 편집기에 붙여넣을 2줄 코드
├── tests/
│   └── test_smoke.py       # 임포트 스모크 테스트
├── requirements.txt
└── README.md
```

> **⚠️ 패키지 이름을 `backend`로 쓰지 않는 이유:** Dataiku 웹앱은 백엔드 코드를
> 실행 폴더 `backend/main.py`에 배치하므로, 공용 패키지를 `backend`로 두면
> 임포트 충돌이 발생합니다. 그래서 패키지명을 **`iplandscape`**로 사용합니다.

---

## 2. 로컬 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run frontend/app.py
```

---

## 3. Dataiku DSS 배포 (요약)

1. `iplandscape/` 패키지를 Dataiku **프로젝트 라이브러리**(`lib/python/`)에 업로드
2. Streamlit 웹앱을 생성하고 코드 편집기에 `dataiku_webapp_code.py`의 2줄을 붙여넣기
3. 코드 환경에 `requirements.txt`의 패키지를 추가

---

## 4. 로드맵 (TBD)

- [ ] 특허 엑셀 업로드 및 컬럼 매핑
- [ ] 랜드스케이프 차트 유형 정의 (버블 맵, 히트맵, 연도×출원인 매트릭스 등)
- [ ] 차트 인터랙션 및 필터
- [ ] 차트/리포트 내보내기

세부 기능은 요구사항이 정해지는 대로 이 저장소에서 개발합니다.
