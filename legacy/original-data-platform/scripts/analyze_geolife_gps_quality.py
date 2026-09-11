"""GeoLife Raw GPS step와 기존 Window Feature 이상치를 수치화한다."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import pandas as pd

from src.common.geo import haversine_distance_km
from src.geolife.raw import GeoLifeFormatError, TrajectoryPoint, iter_trajectory_points


def analyze_raw_quality(
    source: str | Path,
    *,
    max_speed_mps: float = 100.0,
    gap_threshold_seconds: float = 120.0,
    max_altitude_jump_m: float = 500.0,
) -> dict[str, object]:
    counts: Counter[str] = Counter()
    users: set[str] = set()
    trajectories: set[tuple[str, str]] = set()
    speed_examples: list[dict[str, object]] = []
    altitude_examples: list[dict[str, object]] = []
    parse_errors: list[str] = []
    previous: TrajectoryPoint | None = None
    total_points = 0

    def on_error(error: GeoLifeFormatError) -> None:
        parse_errors.append(str(error))

    for point in iter_trajectory_points(source, strict=False, on_error=on_error):
        total_points += 1
        users.add(point.user_id)
        key = (point.user_id, point.trajectory_id)
        trajectories.add(key)
        if previous is None or (previous.user_id, previous.trajectory_id) != key:
            previous = point
            continue
        counts["total_step_count"] += 1
        delta_seconds = (point.timestamp - previous.timestamp).total_seconds()
        if not math.isfinite(delta_seconds):
            counts["invalid_timestamp_count"] += 1
            previous = point
            continue
        if delta_seconds == 0:
            counts["zero_dt_count"] += 1
        elif delta_seconds < 0:
            counts["negative_dt_count"] += 1
        elif delta_seconds > gap_threshold_seconds:
            counts["long_gap_count"] += 1
        if delta_seconds > 0:
            distance_m = haversine_distance_km(
                previous.latitude, previous.longitude, point.latitude, point.longitude
            ) * 1000
            speed_mps = distance_m / delta_seconds
            if speed_mps > max_speed_mps:
                counts["extreme_speed_count"] += 1
                if len(speed_examples) < 10:
                    speed_examples.append(
                        {
                            "user_id": point.user_id,
                            "trajectory_id": point.trajectory_id,
                            "timestamp": point.timestamp.isoformat(sep=" "),
                            "distance_m": distance_m,
                            "delta_seconds": delta_seconds,
                            "speed_mps": speed_mps,
                        }
                    )
        altitude_delta_m = abs(point.altitude_ft - previous.altitude_ft) * 0.3048
        if altitude_delta_m > max_altitude_jump_m:
            counts["altitude_anomaly_count"] += 1
            if len(altitude_examples) < 10:
                altitude_examples.append(
                    {
                        "user_id": point.user_id,
                        "trajectory_id": point.trajectory_id,
                        "timestamp": point.timestamp.isoformat(sep=" "),
                        "altitude_delta_m": altitude_delta_m,
                    }
                )
        previous = point

    return {
        "source": str(source),
        "total_points": total_points,
        "user_count": len(users),
        "trajectory_count": len(trajectories),
        "parse_error_count": len(parse_errors),
        "parse_error_examples": parse_errors[:10],
        "thresholds": {
            "max_speed_mps": max_speed_mps,
            "gap_threshold_seconds": gap_threshold_seconds,
            "max_altitude_jump_m": max_altitude_jump_m,
        },
        "step_counts": dict(counts),
        "speed_examples": speed_examples,
        "altitude_examples": altitude_examples,
    }


def analyze_processed_quality(processed_csv: str | Path) -> dict[str, object]:
    frame = pd.read_csv(processed_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    numeric = frame.select_dtypes(include="number")
    return {
        "processed_csv": str(processed_csv),
        "window_count": len(frame),
        "affected_user_count": int(frame.loc[(frame.valid_step_count == 0) | (frame.displacement_m > frame.distance_m) | (frame.straightness_ratio > 1), "user_id"].nunique()),
        "affected_trajectory_count": int(frame.loc[(frame.valid_step_count == 0) | (frame.displacement_m > frame.distance_m) | (frame.straightness_ratio > 1), ["user_id", "trajectory_id"]].drop_duplicates().shape[0]),
        "nan_count": int(frame.isna().sum().sum()),
        "inf_count": int(numeric.map(lambda value: not math.isfinite(value)).sum().sum()),
        "duplicate_row_count": int(frame.duplicated().sum()),
        "feature_anomaly_count": {
            "valid_step_count_zero": int((frame.valid_step_count == 0).sum()),
            "displacement_gt_distance": int((frame.displacement_m > frame.distance_m + 1e-9).sum()),
            "straightness_gt_1": int((frame.straightness_ratio > 1 + 1e-9).sum()),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--processed-csv")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = analyze_raw_quality(args.source)
    if args.processed_csv:
        result["processed_quality"] = analyze_processed_quality(args.processed_csv)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
