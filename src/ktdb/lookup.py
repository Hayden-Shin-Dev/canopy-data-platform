"""KTDB 표본을 조건별 mode 확률 lookup으로 집계하는 모듈."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from os import PathLike

import pandas as pd


MODE_CLASSES: tuple[str, ...] = ("walk", "bike", "car", "bus", "rail")
DEFAULT_CONTEXT_COLUMNS: tuple[str, ...] = (
    "weekday",
    "time_band",
    "origin_sido",
    "origin_sigungu",
    "od_scope",
    "purpose",
    "commute_direction",
)


def normalize_mode_probabilities(
    counts: Mapping[str, int | float],
    *,
    classes: Sequence[str] = MODE_CLASSES,
) -> dict[str, float]:
    """주어진 mode 건수를 0~1 확률로 바꾸고 누락 class는 0으로 채운다."""

    if not classes or len(set(classes)) != len(classes):
        raise ValueError("classes에는 중복 없는 mode 이름이 하나 이상 필요합니다")
    values = {label: max(float(counts.get(label, 0)), 0.0) for label in classes}
    total = sum(values.values())
    if total == 0:
        return {label: 0.0 for label in classes}
    return {label: value / total for label, value in values.items()}


def _validate_frame(frame: pd.DataFrame, context_columns: Iterable[str]) -> tuple[str, ...]:
    columns = tuple(context_columns)
    required = set(columns) | {"actual_mode"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"lookup 집계에 필요한 컬럼이 없습니다: {missing}")
    invalid = sorted(set(frame["actual_mode"].dropna().astype(str)) - set(MODE_CLASSES))
    if invalid:
        raise ValueError(f"Canopy 5-class가 아닌 mode가 포함되어 있습니다: {invalid}")
    return columns


def _aggregate_level(
    frame: pd.DataFrame,
    context_columns: tuple[str, ...],
    *,
    level: str,
) -> pd.DataFrame:
    group_columns = [*context_columns, "actual_mode"]
    counts = (
        frame.assign(actual_mode=frame["actual_mode"].astype("string"))
        .groupby(group_columns, dropna=False, observed=True)
        .size()
        .rename("mode_count")
        .reset_index()
    )
    if counts.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    context_key_columns = list(context_columns)
    for values, group in counts.groupby(context_key_columns, dropna=False, observed=True, sort=True):
        if not isinstance(values, tuple):
            values = (values,)
        row: dict[str, object] = {
            column: value for column, value in zip(context_columns, values, strict=True)
        }
        mode_counts = dict(zip(group["actual_mode"].astype(str), group["mode_count"], strict=True))
        probabilities = normalize_mode_probabilities(mode_counts)
        row.update(
            {
                "context_level": level,
                "sample_count": int(group["mode_count"].sum()),
                **{f"{mode}_probability": probabilities[mode] for mode in MODE_CLASSES},
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_population_lookup(
    frame: pd.DataFrame,
    *,
    context_columns: Sequence[str] = DEFAULT_CONTEXT_COLUMNS,
    min_samples: int = 30,
    fallback_levels: Sequence[Sequence[str]] | None = None,
) -> pd.DataFrame:
    """조건별 mode 확률을 만들고 표본이 충분한 계층만 반환한다.

    ``fallback_levels``는 낮은 우선순위부터 명시한다. 지정하지 않으면
    전체 context에서 마지막 컬럼을 하나씩 줄이는 계층을 사용한다.
    """

    if min_samples < 1:
        raise ValueError("min_samples는 1 이상이어야 합니다")
    columns = _validate_frame(frame, context_columns)
    if fallback_levels is None:
        levels = [columns[:size] for size in range(len(columns), 0, -1)]
    else:
        levels = [tuple(level) for level in fallback_levels]
        if not levels:
            raise ValueError("fallback_levels에는 하나 이상의 context가 필요합니다")
    tables: list[pd.DataFrame] = []
    for level_columns in levels:
        if not set(level_columns).issubset(columns):
            raise ValueError("fallback context는 기본 context 컬럼 안에서 선택해야 합니다")
        table = _aggregate_level(frame, tuple(level_columns), level="|".join(level_columns))
        if table.empty:
            continue
        table = table[table["sample_count"] >= min_samples].copy()
        if table.empty:
            continue
        tables.append(table)
    if not tables:
        return pd.DataFrame(
            columns=[*columns, "context_level", "sample_count"]
            + [f"{mode}_probability" for mode in MODE_CLASSES]
        )
    result = pd.concat(tables, ignore_index=True, sort=False)
    for column in columns:
        if column not in result:
            result[column] = pd.NA
    return result[
        [*columns, "context_level", "sample_count"]
        + [f"{mode}_probability" for mode in MODE_CLASSES]
    ].sort_values(["context_level", *columns], kind="stable", na_position="last").reset_index(drop=True)


def write_population_lookup(
    frame: pd.DataFrame,
    path: str | PathLike[str],
    *,
    context_columns: Sequence[str] = DEFAULT_CONTEXT_COLUMNS,
    min_samples: int = 30,
) -> pd.DataFrame:
    """lookup을 만들고 재현 가능한 UTF-8 CSV로 저장한다."""

    lookup = build_population_lookup(
        frame,
        context_columns=context_columns,
        min_samples=min_samples,
    )
    lookup.to_csv(path, index=False, encoding="utf-8-sig")
    return lookup
