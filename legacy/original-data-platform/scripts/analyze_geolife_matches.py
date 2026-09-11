"""GeoLife 전체 GPS point의 label 연결 결과를 집계한다."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from src.geolife.label_match import iter_labeled_points
from src.geolife.mode_mapping import canonicalize_mode
from src.geolife.raw import iter_label_intervals, iter_trajectory_points


def analyze_matches(zip_path: str) -> dict[str, object]:
    labels = list(iter_label_intervals(zip_path))
    status_counts: Counter[str] = Counter()
    raw_mode_counts: Counter[str] = Counter()
    canonical_mode_counts: Counter[str] = Counter()
    users_with_matches: set[str] = set()
    total_points = 0
    parse_errors = []

    points = iter_trajectory_points(
        zip_path,
        strict=False,
        on_error=parse_errors.append,
    )
    for labeled_point in iter_labeled_points(points, labels):
        total_points += 1
        status_counts[labeled_point.match_status] += 1
        if labeled_point.match_status == "matched":
            assert labeled_point.mode_raw is not None
            raw_mode_counts[labeled_point.mode_raw] += 1
            canonical_mode = canonicalize_mode(labeled_point.mode_raw)
            if canonical_mode is not None:
                canonical_mode_counts[canonical_mode] += 1
            users_with_matches.add(labeled_point.point.user_id)
        if total_points % 1_000_000 == 0:
            print(f"processed {total_points:,} points", file=sys.stderr)

    return {
        "total_points": total_points,
        "status_counts": dict(sorted(status_counts.items())),
        "matched_raw_mode_counts": dict(sorted(raw_mode_counts.items())),
        "matched_canonical_mode_counts": dict(sorted(canonical_mode_counts.items())),
        "users_with_matches": len(users_with_matches),
        "trajectory_parse_error_count": len(parse_errors),
        "trajectory_parse_error_examples": [str(error) for error in parse_errors[:5]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", help="GeoLife Trajectories 1.3 ZIP 경로")
    args = parser.parse_args()
    print(json.dumps(analyze_matches(args.zip_path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
