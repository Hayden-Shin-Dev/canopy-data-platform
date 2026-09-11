"""시간순 Window prediction을 연속 이동 segment로 병합한다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Segment:
    mode: str
    start_index: int
    end_index: int

    @property
    def window_count(self) -> int:
        return self.end_index - self.start_index + 1


def merge_consecutive_predictions(predictions: Sequence[str]) -> list[Segment]:
    """같은 mode가 연속된 Window를 하나의 segment로 묶는다."""
    if not predictions:
        return []
    segments: list[Segment] = []
    start = 0
    current = predictions[0]
    for index, mode in enumerate(predictions[1:], start=1):
        if mode == current:
            continue
        segments.append(Segment(current, start, index - 1))
        start = index
        current = mode
    segments.append(Segment(current, start, len(predictions) - 1))
    return segments

