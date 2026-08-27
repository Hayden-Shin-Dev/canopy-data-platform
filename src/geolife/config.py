"""GeoLife 전처리에서 사용하는 설정값 모음."""

from __future__ import annotations


# 원본 interval 분포를 확인한 뒤 비교할 Window 후보들이다.
WINDOW_CANDIDATE_SECONDS = (30, 60, 120)

# 이보다 긴 간격은 하나의 연속 GPS step으로 속도·가속도를 계산하지 않는다.
DEFAULT_GAP_THRESHOLD_SECONDS = 120

# Window 생성 시 최소한 필요한 point 수다.
DEFAULT_MIN_POINTS = 2

