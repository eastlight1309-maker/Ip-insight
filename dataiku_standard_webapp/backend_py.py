# ============================================================================
# Dataiku "Standard(코드) 웹앱"의 [Python] 백엔드 탭에 붙여넣을 코드.
#
# 사전 준비:
#   1) 이 저장소의 `exceltranslator/` 폴더 전체를 프로젝트 라이브러리 python/ 아래에
#      복사합니다 (경로: python/exceltranslator/...).  (README 참고)
#   2) 웹앱 설정에서 "Python backend" 를 활성화(Enable)합니다.
#   3) 관리 폴더 2개(excel_translator_input / excel_translator_output)를 만들고,
#      웹앱 설정의 관련 권한(폴더 읽기/쓰기, LLM 사용)을 허용합니다.
#
# 아래 2줄이 전부입니다. 실제 라우트/로직은 exceltranslator/webbackend.py 에 있어
# 라이브러리만 갱신하면 이 편집기 코드는 그대로 두면 됩니다.
# ============================================================================
from exceltranslator.webbackend import register_routes

# `app` 은 Dataiku 표준 웹앱 백엔드가 제공하는 Flask 앱 객체입니다.
register_routes(app)  # noqa: F821
