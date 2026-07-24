"""로컬 실행 진입점: streamlit run frontend/app.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iplandscape.webapp import main

main()
