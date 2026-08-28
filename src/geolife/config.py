"""GeoLife 전처리에서 사용하는 설정값 모음."""

from __future__ import annotations


# 원본 interval 분포를 확인한 뒤 비교할 Window 후보들이다.
WINDOW_CANDIDATE_SECONDS = (30, 60, 120)

# 이보다 긴 간격은 하나의 연속 GPS step으로 속도·가속도를 계산하지 않는다.
DEFAULT_GAP_THRESHOLD_SECONDS = 120

# 정지 비율 계산에 사용할 보수적인 속도 기준이다.
DEFAULT_STOP_THRESHOLD_MPS = 0.5

# Window 생성 시 최소한 필요한 point 수다.
DEFAULT_MIN_POINTS = 2

# mode와 무관하게 GPS step 자체의 품질을 판단하는 기준이다.
DEFAULT_MAX_PLAUSIBLE_SPEED_MPS = 100.0
DEFAULT_MAX_ALTITUDE_JUMP_M = 500.0
