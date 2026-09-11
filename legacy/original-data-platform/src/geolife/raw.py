"""GeoLife Trajectories 1.3 원본 파일을 읽는 최소 parser."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Callable, Iterator


TRAJECTORY_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
LABEL_TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M:%S"
HEADER_LINE_COUNT = 6


class GeoLifeFormatError(ValueError):
    """원본 행이 GeoLife 형식과 맞지 않을 때 발생한다."""


@dataclass(frozen=True)
class TrajectoryPoint:
    user_id: str
    trajectory_id: str
    latitude: float
    longitude: float
    altitude_ft: float
    timestamp: datetime


@dataclass(frozen=True)
class LabelInterval:
    user_id: str
    start_time: datetime
    end_time: datetime
    mode_raw: str


def _is_zip(source: Path) -> bool:
    return source.is_file() and source.suffix.lower() == ".zip"


def _user_id(member_name: str) -> str:
    parts = PurePosixPath(member_name).parts
    try:
        data_index = parts.index("Data")
        return parts[data_index + 1]
    except (ValueError, IndexError) as exc:
        raise GeoLifeFormatError(f"Data 경로에서 user_id를 찾을 수 없습니다: {member_name}") from exc


def _parse_trajectory_row(raw_line: bytes, member_name: str, line_number: int) -> tuple[float, float, float, datetime] | None:
    text = raw_line.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    columns = text.split(",")
    if len(columns) < 7:
        raise GeoLifeFormatError(f"trajectory 열 수가 부족합니다: {member_name}:{line_number}")
    try:
        latitude = float(columns[0])
        longitude = float(columns[1])
        altitude_ft = float(columns[3])
        timestamp = datetime.strptime(
            f"{columns[5]} {columns[6]}", TRAJECTORY_TIMESTAMP_FORMAT
        )
    except ValueError as exc:
        raise GeoLifeFormatError(f"trajectory 값 형식이 잘못됐습니다: {member_name}:{line_number}") from exc
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise GeoLifeFormatError(f"좌표 범위를 벗어났습니다: {member_name}:{line_number}")
    return latitude, longitude, altitude_ft, timestamp


def _iter_trajectory_stream(
    stream: BinaryIO,
    member_name: str,
    user_id: str,
    *,
    strict: bool,
    on_error: Callable[[GeoLifeFormatError], None] | None,
) -> Iterator[TrajectoryPoint]:
    for _ in range(HEADER_LINE_COUNT):
        stream.readline()
    trajectory_id = PurePosixPath(member_name).stem
    for line_number, raw_line in enumerate(stream, start=HEADER_LINE_COUNT + 1):
        try:
            parsed = _parse_trajectory_row(raw_line, member_name, line_number)
        except GeoLifeFormatError as error:
            if strict:
                raise
            if on_error is not None:
                on_error(error)
            continue
        if parsed is None:
            continue
        latitude, longitude, altitude_ft, timestamp = parsed
        yield TrajectoryPoint(
            user_id=user_id,
            trajectory_id=trajectory_id,
            latitude=latitude,
            longitude=longitude,
            altitude_ft=altitude_ft,
            timestamp=timestamp,
        )


def _iter_label_stream(stream: BinaryIO, member_name: str, user_id: str) -> Iterator[LabelInterval]:
    for line_number, raw_line in enumerate(stream, start=1):
        columns = raw_line.decode("utf-8-sig", errors="replace").rstrip("\r\n").split("\t")
        if line_number == 1 and columns == ["Start Time", "End Time", "Transportation Mode"]:
            continue
        if len(columns) != 3:
            raise GeoLifeFormatError(f"label 열 수가 잘못됐습니다: {member_name}:{line_number}")
        try:
            start_time = datetime.strptime(columns[0], LABEL_TIMESTAMP_FORMAT)
            end_time = datetime.strptime(columns[1], LABEL_TIMESTAMP_FORMAT)
        except ValueError as exc:
            raise GeoLifeFormatError(f"label 시간 형식이 잘못됐습니다: {member_name}:{line_number}") from exc
        if end_time < start_time:
            raise GeoLifeFormatError(f"label 시간 순서가 잘못됐습니다: {member_name}:{line_number}")
        mode_raw = columns[2].strip()
        if not mode_raw:
            raise GeoLifeFormatError(f"label mode가 비어 있습니다: {member_name}:{line_number}")
        yield LabelInterval(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            mode_raw=mode_raw,
        )


def iter_trajectory_points(
    source: str | Path,
    *,
    strict: bool = True,
    on_error: Callable[[GeoLifeFormatError], None] | None = None,
) -> Iterator[TrajectoryPoint]:
    """ZIP 또는 압축 해제된 GeoLife 디렉터리에서 trajectory point를 순서대로 읽는다."""
    source_path = Path(source)
    if _is_zip(source_path):
        with zipfile.ZipFile(source_path) as archive:
            members = sorted(
                (info for info in archive.infolist() if info.filename.lower().endswith(".plt")),
                key=lambda info: info.filename,
            )
            for member in members:
                with archive.open(member) as stream:
                    yield from _iter_trajectory_stream(
                        stream,
                        member.filename,
                        _user_id(member.filename),
                        strict=strict,
                        on_error=on_error,
                    )
        return

    for path in sorted(source_path.glob("Data/*/Trajectory/*.plt")):
        with path.open("rb") as stream:
            yield from _iter_trajectory_stream(
                stream,
                path.as_posix(),
                path.parent.parent.name,
                strict=strict,
                on_error=on_error,
            )


def iter_label_intervals(source: str | Path) -> Iterator[LabelInterval]:
    """ZIP 또는 압축 해제된 GeoLife 디렉터리에서 원본 label interval을 읽는다."""
    source_path = Path(source)
    if _is_zip(source_path):
        with zipfile.ZipFile(source_path) as archive:
            members = sorted(
                (info for info in archive.infolist() if PurePosixPath(info.filename).name == "labels.txt"),
                key=lambda info: info.filename,
            )
            for member in members:
                with archive.open(member) as stream:
                    yield from _iter_label_stream(stream, member.filename, _user_id(member.filename))
        return

    for path in sorted(source_path.glob("Data/*/labels.txt")):
        with path.open("rb") as stream:
            yield from _iter_label_stream(stream, path.as_posix(), path.parent.name)
