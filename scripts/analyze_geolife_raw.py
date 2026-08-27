"""GeoLife Trajectories 1.3 원본 ZIP의 구조와 기본 품질을 확인한다."""

from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import PurePosixPath
from typing import BinaryIO


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
LABEL_TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M:%S"
USER_PATTERN = re.compile(r"/Data/([^/]+)/")


def _percentiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p50": None, "p95": None, "p99": None}
    values = sorted(values)

    def pick(percentile: float) -> float:
        index = min(len(values) - 1, math.ceil(percentile * len(values)) - 1)
        return values[index]

    return {"p50": pick(0.50), "p95": pick(0.95), "p99": pick(0.99)}


def _trajectory_sample(stream: BinaryIO) -> dict[str, object]:
    for _ in range(6):
        stream.readline()

    points = 0
    malformed_rows = 0
    invalid_coordinates = 0
    non_monotonic_steps = 0
    intervals: list[float] = []
    latitudes: list[float] = []
    longitudes: list[float] = []
    timestamps: list[datetime] = []
    previous_timestamp: datetime | None = None

    for raw_line in stream:
        columns = raw_line.decode("utf-8", errors="replace").strip().split(",")
        if len(columns) < 7:
            if columns != [""]:
                malformed_rows += 1
            continue
        try:
            latitude = float(columns[0])
            longitude = float(columns[1])
            timestamp = datetime.strptime(
                f"{columns[5]} {columns[6]}", TIMESTAMP_FORMAT
            )
        except ValueError:
            malformed_rows += 1
            continue

        points += 1
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            invalid_coordinates += 1
        latitudes.append(latitude)
        longitudes.append(longitude)
        timestamps.append(timestamp)
        if previous_timestamp is not None:
            interval = (timestamp - previous_timestamp).total_seconds()
            intervals.append(interval)
            if interval <= 0:
                non_monotonic_steps += 1
        previous_timestamp = timestamp

    return {
        "points": points,
        "malformed_rows": malformed_rows,
        "invalid_coordinates": invalid_coordinates,
        "non_monotonic_steps": non_monotonic_steps,
        "interval_seconds": _percentiles(intervals),
        "coordinate_bounds": {
            "latitude_min": min(latitudes) if latitudes else None,
            "latitude_max": max(latitudes) if latitudes else None,
            "longitude_min": min(longitudes) if longitudes else None,
            "longitude_max": max(longitudes) if longitudes else None,
        },
        "timestamp_range": {
            "start": timestamps[0].isoformat(sep=" ") if timestamps else None,
            "end": timestamps[-1].isoformat(sep=" ") if timestamps else None,
        },
    }


def _count_trajectory_points(stream: BinaryIO) -> tuple[int, int]:
    for _ in range(6):
        stream.readline()
    points = 0
    malformed_rows = 0
    for raw_line in stream:
        columns = raw_line.decode("utf-8", errors="replace").strip().split(",")
        if len(columns) >= 7:
            points += 1
        elif columns != [""]:
            malformed_rows += 1
    return points, malformed_rows


def _read_labels(stream: BinaryIO) -> tuple[int, int, Counter[str], datetime | None, datetime | None]:
    rows = 0
    malformed_rows = 0
    modes: Counter[str] = Counter()
    starts: list[datetime] = []
    ends: list[datetime] = []
    for line_number, raw_line in enumerate(stream):
        columns = raw_line.decode("utf-8-sig", errors="replace").rstrip("\r\n").split("\t")
        if line_number == 0:
            continue
        if len(columns) != 3:
            if raw_line.strip():
                malformed_rows += 1
            continue
        try:
            start = datetime.strptime(columns[0], LABEL_TIMESTAMP_FORMAT)
            end = datetime.strptime(columns[1], LABEL_TIMESTAMP_FORMAT)
        except ValueError:
            malformed_rows += 1
            continue
        rows += 1
        modes[columns[2].strip()] += 1
        starts.append(start)
        ends.append(end)
    return rows, malformed_rows, modes, min(starts, default=None), max(ends, default=None)


def analyze_zip(zip_path: str, sample_size: int = 20) -> dict[str, object]:
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        trajectory_members = sorted(
            (member for member in members if member.filename.lower().endswith(".plt")),
            key=lambda member: member.filename,
        )
        label_members = sorted(
            (member for member in members if PurePosixPath(member.filename).name == "labels.txt"),
            key=lambda member: member.filename,
        )
        data_users = sorted(
            {
                match.group(1)
                for member in trajectory_members
                if (match := USER_PATTERN.search(member.filename))
            }
        )

        total_points = 0
        total_malformed_rows = 0
        nonempty_trajectories = 0
        for member in trajectory_members:
            with archive.open(member) as stream:
                points, malformed_rows = _count_trajectory_points(stream)
            total_points += points
            total_malformed_rows += malformed_rows
            nonempty_trajectories += int(points > 0)

        label_rows = 0
        label_malformed_rows = 0
        label_modes: Counter[str] = Counter()
        label_starts: list[datetime] = []
        label_ends: list[datetime] = []
        for member in label_members:
            with archive.open(member) as stream:
                rows, malformed, modes, start, end = _read_labels(stream)
            label_rows += rows
            label_malformed_rows += malformed
            label_modes.update(modes)
            if start is not None:
                label_starts.append(start)
            if end is not None:
                label_ends.append(end)

        samples: dict[str, object] = {}
        for member in trajectory_members[:sample_size]:
            with archive.open(member) as stream:
                samples[member.filename] = _trajectory_sample(stream)

    return {
        "source": {
            "zip_path": zip_path,
            "member_count": len(members),
            "compressed_bytes": sum(member.compress_size for member in members),
            "uncompressed_bytes": sum(member.file_size for member in members),
        },
        "trajectory": {
            "file_count": len(trajectory_members),
            "nonempty_file_count": nonempty_trajectories,
            "user_count": len(data_users),
            "user_id_range": {
                "first": data_users[0] if data_users else None,
                "last": data_users[-1] if data_users else None,
            },
            "point_count": total_points,
            "malformed_rows": total_malformed_rows,
            "sample_count": min(sample_size, len(trajectory_members)),
            "samples": samples,
        },
        "labels": {
            "file_count": len(label_members),
            "row_count": label_rows,
            "malformed_rows": label_malformed_rows,
            "user_count": len(
                {
                    PurePosixPath(member.filename).parts[-2]
                    for member in label_members
                    if len(PurePosixPath(member.filename).parts) >= 2
                }
            ),
            "raw_mode_counts": dict(sorted(label_modes.items())),
            "time_range": {
                "start": min(label_starts).isoformat(sep=" ") if label_starts else None,
                "end": max(label_ends).isoformat(sep=" ") if label_ends else None,
            },
        },
        "other_members": [
            member.filename
            for member in members
            if member.file_size
            and not member.filename.lower().endswith(".plt")
            and PurePosixPath(member.filename).name != "labels.txt"
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", help="GeoLife Trajectories 1.3 ZIP 경로")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="전체 구조 검증에 사용할 trajectory 샘플 수 (기본값: 20)",
    )
    args = parser.parse_args()
    result = analyze_zip(args.zip_path, sample_size=args.sample_size)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
