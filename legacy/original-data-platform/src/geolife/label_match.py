"""GPS timestamp와 GeoLife label interval을 연결한다."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Iterator, Literal

from src.geolife.raw import LabelInterval, TrajectoryPoint


MatchStatus = Literal["matched", "unmatched", "ambiguous"]


@dataclass(frozen=True)
class LabeledPoint:
    point: TrajectoryPoint
    mode_raw: str | None
    match_status: MatchStatus


def match_point(point: TrajectoryPoint, intervals: Iterable[LabelInterval]) -> LabeledPoint:
    """한 point를 interval에 연결하고, 충돌은 ambiguous로 남긴다."""
    candidates = [
        interval
        for interval in intervals
        if interval.user_id == point.user_id
        and interval.start_time <= point.timestamp <= interval.end_time
    ]
    if len(candidates) == 1:
        return LabeledPoint(point=point, mode_raw=candidates[0].mode_raw, match_status="matched")
    if len(candidates) > 1:
        return LabeledPoint(point=point, mode_raw=None, match_status="ambiguous")
    return LabeledPoint(point=point, mode_raw=None, match_status="unmatched")


def iter_labeled_points(
    points: Iterable[TrajectoryPoint], labels: Iterable[LabelInterval]
) -> Iterator[LabeledPoint]:
    """전체 label을 user별로 정렬한 뒤 point stream에 순서대로 적용한다."""
    labels_by_user: dict[str, list[LabelInterval]] = defaultdict(list)
    for interval in labels:
        labels_by_user[interval.user_id].append(interval)
    for user_intervals in labels_by_user.values():
        user_intervals.sort(key=lambda interval: (interval.start_time, interval.end_time))

    positions: dict[str, int] = defaultdict(int)
    for point in points:
        user_intervals = labels_by_user.get(point.user_id, [])
        position = positions[point.user_id]
        while position < len(user_intervals) and user_intervals[position].end_time < point.timestamp:
            position += 1
        positions[point.user_id] = position

        active = []
        candidate_index = position
        while candidate_index < len(user_intervals):
            interval = user_intervals[candidate_index]
            if interval.start_time > point.timestamp:
                break
            if point.timestamp <= interval.end_time:
                active.append(interval)
            candidate_index += 1
        if len(active) == 1:
            yield LabeledPoint(point=point, mode_raw=active[0].mode_raw, match_status="matched")
        elif active:
            yield LabeledPoint(point=point, mode_raw=None, match_status="ambiguous")
        else:
            yield LabeledPoint(point=point, mode_raw=None, match_status="unmatched")
