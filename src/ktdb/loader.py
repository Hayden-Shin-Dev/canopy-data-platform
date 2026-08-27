"""KTDB 개인·이동 CSV를 원본 그대로 읽는 loader."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from src.common.encoding import detect_encoding

from .schema import PERSON_COLUMNS, trip_columns


def _read_csv(path: Path, columns: tuple[str, ...], **kwargs: object) -> pd.DataFrame:
    """코드와 식별자의 앞자리 보존을 위해 모든 입력을 문자열로 읽는다."""

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    encoding = detect_encoding(path)
    return pd.read_csv(
        path,
        encoding=encoding,
        usecols=list(columns),
        dtype="string",
        keep_default_na=False,
        na_filter=False,
        **kwargs,
    )


def load_person_table(path: Path) -> pd.DataFrame:
    """개인 CSV에서 조인에 필요한 idx와 기준일만 읽는다."""

    frame = _read_csv(path, PERSON_COLUMNS)
    frame["idx"] = frame["idx"].str.strip()
    frame["DATE"] = frame["DATE"].str.strip()
    if frame["idx"].eq("").any():
        raise ValueError("개인 CSV에 빈 idx가 있음")
    if frame["idx"].duplicated().any():
        raise ValueError("개인 CSV의 idx가 중복됨")
    return frame


def iter_trip_chunks(path: Path, chunksize: int = 50_000) -> Iterator[pd.DataFrame]:
    """이동 CSV를 정해진 행 수만큼 나누어 순서대로 반환한다."""

    if chunksize <= 0:
        raise ValueError("chunksize는 양수여야 함")
    reader = _read_csv(path, trip_columns(), chunksize=chunksize)
    for chunk in reader:
        for column in chunk.columns:
            chunk[column] = chunk[column].str.strip()
        yield chunk


def validate_trip_person_keys(
    trip_chunk: pd.DataFrame,
    person_ids: pd.Index,
) -> pd.Series:
    """이동 chunk의 idx가 개인 표에 존재하는지 행별로 표시한다."""

    if "idx" not in trip_chunk.columns:
        raise ValueError("이동 chunk에 idx가 없음")
    return trip_chunk["idx"].isin(person_ids)

