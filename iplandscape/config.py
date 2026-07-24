"""환경변수 기반 설정."""

import os

APP_TITLE = "IP_Landscape chart"

# Dataiku 관리 폴더 이름 (Dataiku 배포 시 사용, 로컬에서는 무시)
INPUT_FOLDER_NAME = os.getenv("IPL_INPUT_FOLDER", "ipl_input")
OUTPUT_FOLDER_NAME = os.getenv("IPL_OUTPUT_FOLDER", "ipl_output")
