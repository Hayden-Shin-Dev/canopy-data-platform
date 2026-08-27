"""GeoLife trajectory별 GPS sampling interval을 집계한다."""

from __future__ import annotations

import argparse
import json
from collections import Counter

from src.geolife.raw import iter_trajectory_points


def _quantile(counts: Counter[int], total: int, fraction: float) -> int | None:
    if total == 0:
        return None
    target = max(1, int(total * fraction + 0.999999))
    cumulative = 0
    for seconds in sorted(counts):
        cumulative += counts[seconds]
        if cumulative >= target:
            return seconds
    return max(counts)


def analyze_sampling(zip_path: str, gap_threshold_seconds: int = 120) -> dict[str, object]:
    interval_counts: Counter[int] = Counter()
    trajectory_count = 0
    valid_points = 0
    positive_steps = 0
    zero_or_negative_steps = 0
    gap_steps = 0
    previous_key: tuple[str, str] | None = None
    previous_timestamp = None

    for point in iter_trajectory_points(zip_path, strict=False):
        valid_points += 1
        current_key = (point.user_id, point.trajectory_id)
        if current_key != previous_key:
            trajectory_count += 1
            previous_key = current_key
            previous_timestamp = point.timestamp
            continue
        delta_seconds = int((point.timestamp - previous_timestamp).total_seconds())
        previous_timestamp = point.timestamp
        if delta_seconds <= 0:
            zero_or_negative_steps += 1
            continue
        positive_steps += 1
        interval_counts[delta_seconds] += 1
        if delta_seconds > gap_threshold_seconds:
            gap_steps += 1

    return {
        "valid_points": valid_points,
        "trajectory_count": trajectory_count,
        "positive_steps": positive_steps,
        "zero_or_negative_steps": zero_or_negative_steps,
        "gap_threshold_seconds": gap_threshold_seconds,
        "gap_steps": gap_steps,
        "interval_seconds": {
            "p50": _quantile(interval_counts, positive_steps, 0.50),
            "p75": _quantile(interval_counts, positive_steps, 0.75),
            "p90": _quantile(interval_counts, positive_steps, 0.90),
            "p95": _quantile(interval_counts, positive_steps, 0.95),
            "max": max(interval_counts, default=None),
        },
        "most_common_intervals": [
            {"seconds": seconds, "count": count}
            for seconds, count in interval_counts.most_common(10)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", help="GeoLife Trajectories 1.3 ZIP 경로")
    parser.add_argument("--gap-threshold-seconds", type=int, default=120)
    args = parser.parse_args()
    print(json.dumps(analyze_sampling(args.zip_path, args.gap_threshold_seconds), indent=2))


if __name__ == "__main__":
    main()
