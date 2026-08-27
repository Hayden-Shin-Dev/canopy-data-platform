"""GeoLife 원본 mode를 Canopy의 5개 mode로 변환하는 정책."""

from __future__ import annotations

from types import MappingProxyType


CANOPY_MODES = ("walk", "bike", "car", "bus", "rail")

# 동일한 이동수단으로 해석할 수 있는 값만 명시적으로 합친다.
RAW_TO_CANOPY = MappingProxyType(
    {
        "walk": "walk",
        "bike": "bike",
        "car": "car",
        "bus": "bus",
        "taxi": "car",
        "subway": "rail",
        "train": "rail",
    }
)

# target 5개와 등가라고 볼 근거가 없는 활동·교통수단은 학습에서 제외한다.
EXCLUDED_RAW_MODES = frozenset({"airplane", "boat", "motorcycle", "run"})


def canonicalize_mode(mode_raw: str) -> str | None:
    """원본 mode를 canonical mode로 바꾸고, 제외 mode는 None을 반환한다."""
    normalized = mode_raw.strip().lower()
    if normalized in RAW_TO_CANOPY:
        return RAW_TO_CANOPY[normalized]
    if normalized in EXCLUDED_RAW_MODES:
        return None
    raise ValueError(f"정의되지 않은 GeoLife raw mode입니다: {mode_raw!r}")

