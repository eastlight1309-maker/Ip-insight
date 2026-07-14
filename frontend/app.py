"""IP Insight — 로컬 실행용 진입점 (얇은 래퍼).

실제 UI 코드는 재사용/배포 편의를 위해 `ipinsight/webapp.py` 에 있다.
로컬:    streamlit run frontend/app.py
Dataiku: 웹앱 편집기에는 아래 2줄만 넣으면 된다(§README 참고).

    from ipinsight.webapp import main
    main()
"""

from __future__ import annotations

import os
import sys

# 로컬 실행 시 프로젝트 루트를 import 경로에 추가.
# (Dataiku에서는 프로젝트 라이브러리 python/ 이 자동으로 sys.path 에 포함됨)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ipinsight.webapp import main  # noqa: E402

main()
