"""패키지 임포트 스모크 테스트."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import():
    import iplandscape
    from iplandscape import config, webapp

    assert iplandscape.__version__
    assert config.APP_TITLE == "IP_Landscape chart"
    assert callable(webapp.main)
