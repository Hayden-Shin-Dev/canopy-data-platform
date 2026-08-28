"""GeoLife 원본에서 Window Feature 학습 CSV를 재생성한다."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from src.geolife.config import DEFAULT_GAP_THRESHOLD_SECONDS, DEFAULT_MIN_POINTS, DEFAULT_STOP_THRESHOLD_MPS
from src.geolife.gps_quality import GpsQualityPolicy, GpsQualityStats, iter_quality_points
from src.geolife.label_match import iter_labeled_points
from src.geolife.labeled_windows import iter_labeled_time_windows
from src.geolife.raw import iter_label_intervals, iter_trajectory_points
from src.geolife.window_features import compute_window_features
from src.geolife.window_labels import summarize_window_labels


FEATURE_COLUMNS = (
    "point_count",
    "observed_duration_sec",
    "distance_m",
    "displacement_m",
    "straightness_ratio",
    "mean_speed_mps",
    "max_speed_mps",
    "speed_std_mps",
    "mean_abs_acceleration_mps2",
    "acceleration_std_mps2",
    "stop_ratio",
    "mean_heading_change_deg",
    "altitude_range_m",
    "avg_sampling_interval_sec",
    "valid_step_count",
    "gap_step_count",
)


def build_window_dataset(
    zip_path: str | Path,
    output_csv: str | Path,
    *,
    window_seconds: int = 60,
    min_points: int = DEFAULT_MIN_POINTS,
    min_label_coverage: float = 0.5,
    apply_gps_quality: bool = True,
) -> dict[str, object]:
    if not 0 < min_label_coverage <= 1:
        raise ValueError("min_label_coverage는 0보다 크고 1 이하여야 합니다")
    labels = list(iter_label_intervals(zip_path))
    parse_errors = []
    raw_points = iter_trajectory_points(
        zip_path,
        strict=False,
        on_error=parse_errors.append,
    )
    quality_stats = GpsQualityStats()
    points = (
        iter_quality_points(raw_points, stats=quality_stats)
        if apply_gps_quality
        else raw_points
    )
    windows = iter_labeled_time_windows(
        iter_labeled_points(points, labels),
        window_seconds=window_seconds,
        min_points=min_points,
    )

    window_status_counts: Counter[str] = Counter()
    selected_mode_counts: Counter[str] = Counter()
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "user_id",
        "trajectory_id",
        "window_start",
        "window_end",
        "canonical_mode",
        "label_coverage",
        "matched_point_count",
        "ambiguous_point_count",
        "excluded_point_count",
        *FEATURE_COLUMNS,
    ]
    selected_window_count = 0
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for window in windows:
            label_summary = summarize_window_labels(window.points)
            window_status_counts[label_summary.status] += 1
            if label_summary.status != "labeled" or label_summary.coverage < min_label_coverage:
                continue
            features = compute_window_features(
                [item.point for item in window.points],
                gap_threshold_seconds=DEFAULT_GAP_THRESHOLD_SECONDS,
                stop_threshold_mps=DEFAULT_STOP_THRESHOLD_MPS,
            )
            row: dict[str, object] = {
                "user_id": window.user_id,
                "trajectory_id": window.trajectory_id,
                "window_start": window.window_start.isoformat(sep=" "),
                "window_end": window.window_end.isoformat(sep=" "),
                "canonical_mode": label_summary.canonical_mode,
                "label_coverage": label_summary.coverage,
                "matched_point_count": label_summary.matched_point_count,
                "ambiguous_point_count": label_summary.ambiguous_point_count,
                "excluded_point_count": label_summary.excluded_point_count,
                **features,
            }
            writer.writerow(row)
            selected_window_count += 1
            selected_mode_counts[str(label_summary.canonical_mode)] += 1

    summary = {
        "source": str(zip_path),
        "output_csv": str(output_path),
        "window_seconds": window_seconds,
        "min_points": min_points,
        "min_label_coverage": min_label_coverage,
        "window_status_counts": dict(sorted(window_status_counts.items())),
        "selected_window_count": selected_window_count,
        "selected_mode_counts": dict(sorted(selected_mode_counts.items())),
        "trajectory_parse_error_count": len(parse_errors),
        "trajectory_parse_error_examples": [str(error) for error in parse_errors[:5]],
        "gps_quality": {
            "enabled": apply_gps_quality,
            "policy": GpsQualityPolicy().__dict__ if apply_gps_quality else None,
            "stats": quality_stats.__dict__ if apply_gps_quality else None,
        },
    }
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", help="GeoLife Trajectories 1.3 ZIP 경로")
    parser.add_argument("output_csv", help="생성할 Window CSV 경로")
    parser.add_argument("--window-seconds", type=int, default=60)
    parser.add_argument("--min-points", type=int, default=DEFAULT_MIN_POINTS)
    parser.add_argument("--min-label-coverage", type=float, default=0.5)
    parser.add_argument("--skip-gps-quality", action="store_true")
    args = parser.parse_args()
    result = build_window_dataset(
        args.zip_path,
        args.output_csv,
        window_seconds=args.window_seconds,
        min_points=args.min_points,
        min_label_coverage=args.min_label_coverage,
        apply_gps_quality=not args.skip_gps_quality,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
