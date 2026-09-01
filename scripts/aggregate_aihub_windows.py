"""Aggregate adjacent one-minute AI-Hub rows into duration-matched windows."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.aihub.features import AIHUB_FEATURE_COLUMNS


def aggregate(input_csv: str | Path, output_csv: str | Path) -> int:
    frame = pd.read_csv(input_csv, encoding="utf-8-sig")
    required = {"user_id", "window_start", "window_end", "canonical_mode", "split", *AIHUB_FEATURE_COLUMNS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"AI-Hub window table is missing columns: {missing}")
    frame["window_start"] = pd.to_datetime(frame["window_start"], errors="raise")
    frame["window_end"] = pd.to_datetime(frame["window_end"], errors="raise")
    frame = frame.sort_values(["user_id", "window_start"]).reset_index(drop=True)
    rows: list[dict[str, object]] = []
    for user_id, group in frame.groupby("user_id", sort=False):
        group = group.reset_index(drop=True)
        index = 0
        while index + 1 < len(group):
            left, right = group.iloc[index], group.iloc[index + 1]
            if left.canonical_mode != right.canonical_mode:
                index += 1
                continue
            gap = right.window_start - left.window_end
            if gap.total_seconds() < 0 or gap.total_seconds() > 30:
                index += 1
                continue
            left_weight = max(float(left.valid_step_count), 1.0)
            right_weight = max(float(right.valid_step_count), 1.0)
            weight = left_weight + right_weight
            weighted = lambda column: (float(left[column]) * left_weight + float(right[column]) * right_weight) / weight
            distance = float(left.distance_m) + float(right.distance_m)
            row: dict[str, object] = {
                "user_id": user_id,
                "trajectory_id": f"{left.trajectory_id}__{right.trajectory_id}",
                "source_class": left.source_class,
                "canonical_mode": left.canonical_mode,
                "window_start": left.window_start,
                "window_end": right.window_end,
                "split": left.split,
                "raw_point_count": int(left.raw_point_count + right.raw_point_count),
                "missing_coordinate_count": int(left.missing_coordinate_count + right.missing_coordinate_count),
                "invalid_coordinate_count": int(left.invalid_coordinate_count + right.invalid_coordinate_count),
                "duplicate_timestamp_count": int(left.duplicate_timestamp_count + right.duplicate_timestamp_count),
                "backwards_timestamp_count": int(left.backwards_timestamp_count + right.backwards_timestamp_count),
                "gap_count": int(left.gap_count + right.gap_count),
                "raw_label_values": "",
                "point_count": int(left.point_count + right.point_count),
                "observed_duration_sec": (right.window_end - left.window_start).total_seconds(),
                "distance_m": distance,
                "displacement_m": float(left.displacement_m + right.displacement_m),
                "straightness_ratio": float(left.displacement_m + right.displacement_m) / distance if distance else 0.0,
                "mean_speed_mps": weighted("mean_speed_mps"),
                "max_speed_mps": max(float(left.max_speed_mps), float(right.max_speed_mps)),
                "speed_std_mps": weighted("speed_std_mps"),
                "mean_abs_acceleration_mps2": weighted("mean_abs_acceleration_mps2"),
                "acceleration_std_mps2": weighted("acceleration_std_mps2"),
                "stop_ratio": weighted("stop_ratio"),
                "mean_heading_change_deg": weighted("mean_heading_change_deg"),
                "altitude_range_m": max(float(left.altitude_range_m), float(right.altitude_range_m)),
                "avg_sampling_interval_sec": weighted("avg_sampling_interval_sec"),
                "valid_step_count": int(left.valid_step_count + right.valid_step_count),
                "gap_step_count": int(left.gap_step_count + right.gap_step_count),
                "accuracy_mean_m": weighted("accuracy_mean_m"),
                "accuracy_std_m": weighted("accuracy_std_m"),
                "accuracy_missing_ratio": weighted("accuracy_missing_ratio"),
                "altitude_missing_ratio": weighted("altitude_missing_ratio"),
                "valid_point_ratio": weighted("valid_point_ratio"),
            }
            rows.append(row)
            index += 2
    columns = [*frame.columns]
    result = pd.DataFrame(rows, columns=columns)
    result.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return len(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    args = parser.parse_args()
    print(aggregate(args.input_csv, args.output_csv))


if __name__ == "__main__":
    main()
