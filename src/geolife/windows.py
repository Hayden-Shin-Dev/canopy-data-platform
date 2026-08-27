"""GeoLife point stream을 trajectory별 고정 시간 Window로 나눈다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Iterator

from src.geolife.raw import TrajectoryPoint


@dataclass(frozen=True)
class TimeWindow:
    user_id: str
    trajectory_id: str
    window_start: datetime
    window_end: datetime
    points: tuple[TrajectoryPoint, ...]


def iter_time_windows(
    points: Iterable[TrajectoryPoint],
    *,
    window_seconds: int,
    min_points: int = 2,
) -> Iterator[TimeWindow]:
    """trajectory 첫 point를 anchor로 삼아 비어 있지 않은 Window를 반환한다."""
    if window_seconds <= 0:
        raise ValueError("window_seconds는 양수여야 합니다")
    if min_points <= 0:
        raise ValueError("min_points는 양수여야 합니다")

    current_key: tuple[str, str] | None = None
    anchor = None
    bucket_index = None
    buffer: list[TrajectoryPoint] = []

    def flush() -> TimeWindow | None:
        if current_key is None or anchor is None or bucket_index is None or len(buffer) < min_points:
            return None
        start = anchor + timedelta(seconds=bucket_index * window_seconds)
        return TimeWindow(
            user_id=current_key[0],
            trajectory_id=current_key[1],
            window_start=start,
            window_end=start + timedelta(seconds=window_seconds),
            points=tuple(buffer),
        )

    for point in points:
        point_key = (point.user_id, point.trajectory_id)
        if point_key != current_key:
            previous = flush()
            if previous is not None:
                yield previous
            current_key = point_key
            anchor = point.timestamp
            bucket_index = 0
            buffer = [point]
            continue

        assert anchor is not None
        next_bucket = int((point.timestamp - anchor).total_seconds() // window_seconds)
        if next_bucket < bucket_index:
            raise ValueError(
                f"trajectory timestamp가 이전 Window로 돌아갔습니다: {point.user_id}/{point.trajectory_id}"
            )
        if next_bucket != bucket_index:
            previous = flush()
            if previous is not None:
                yield previous
            bucket_index = next_bucket
            buffer = [point]
        else:
            buffer.append(point)

    previous = flush()
    if previous is not None:
        yield previous
