"""Window 내부 label 분포를 요약하고 충돌을 보존한다."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal, Sequence

from src.geolife.label_match import LabeledPoint
from src.geolife.mode_mapping import canonicalize_mode


WindowLabelStatus = Literal["labeled", "unlabeled", "ambiguous"]


@dataclass(frozen=True)
class WindowLabelSummary:
    canonical_mode: str | None
    status: WindowLabelStatus
    total_point_count: int
    matched_point_count: int
    ambiguous_point_count: int
    excluded_point_count: int
    mode_counts: dict[str, int]
    dominant_mode_point_count: int
    canonical_mode_purity: float
    distinct_mode_count: int
    is_transition_window: bool

    @property
    def coverage(self) -> float:
        return self.matched_point_count / self.total_point_count if self.total_point_count else 0.0


def summarize_window_labels(points: Sequence[LabeledPoint]) -> WindowLabelSummary:
    """canonical mode별 point 수를 세고 유일한 최다 mode만 후보로 반환한다."""
    mode_counts: Counter[str] = Counter()
    ambiguous_point_count = 0
    excluded_point_count = 0
    for labeled_point in points:
        if labeled_point.match_status == "ambiguous":
            ambiguous_point_count += 1
            continue
        if labeled_point.match_status != "matched":
            continue
        assert labeled_point.mode_raw is not None
        canonical_mode = canonicalize_mode(labeled_point.mode_raw)
        if canonical_mode is None:
            excluded_point_count += 1
        else:
            mode_counts[canonical_mode] += 1

    canonical_labeled_count = sum(mode_counts.values())
    dominant_mode_point_count = max(mode_counts.values(), default=0)
    canonical_mode_purity = (
        dominant_mode_point_count / canonical_labeled_count if canonical_labeled_count else 0.0
    )
    distinct_mode_count = len(mode_counts)
    is_transition_window = distinct_mode_count >= 2
    matched_point_count = canonical_labeled_count + excluded_point_count
    if not mode_counts:
        status: WindowLabelStatus = "unlabeled"
        canonical_mode = None
    else:
        highest = max(mode_counts.values())
        winners = [mode for mode, count in mode_counts.items() if count == highest]
        if len(winners) == 1:
            status = "labeled"
            canonical_mode = winners[0]
        else:
            status = "ambiguous"
            canonical_mode = None

    return WindowLabelSummary(
        canonical_mode=canonical_mode,
        status=status,
        total_point_count=len(points),
        matched_point_count=matched_point_count,
        ambiguous_point_count=ambiguous_point_count,
        excluded_point_count=excluded_point_count,
        mode_counts=dict(sorted(mode_counts.items())),
        dominant_mode_point_count=dominant_mode_point_count,
        canonical_mode_purity=canonical_mode_purity,
        distinct_mode_count=distinct_mode_count,
        is_transition_window=is_transition_window,
    )

