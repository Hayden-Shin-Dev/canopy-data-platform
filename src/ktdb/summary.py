"""KTDB 처리 결과의 행 수, class 분포, 결측률을 계산한다."""

from __future__ import annotations

import json
from collections import Counter
from os import PathLike
from pathlib import Path

import pandas as pd

from .lookup import MODE_CLASSES
from .schema import MODEL_FEATURES


def summarize_frame(frame: pd.DataFrame) -> dict[str, object]:
    """이미 읽은 feature frame을 JSON으로 저장 가능한 지표로 요약한다."""

    row_count = len(frame)
    summary: dict[str, object] = {
        "row_count": row_count,
        "class_distribution": {},
        "split_distribution": {},
        "commute_direction_distribution": {},
        "missing_rate": {},
    }
    if "actual_mode" in frame.columns:
        counts = frame["actual_mode"].astype("string").value_counts(dropna=False)
        summary["class_distribution"] = {
            str(label): int(count) for label, count in counts.items()
        }
        summary["unsupported_mode_count"] = int(
            (~frame["actual_mode"].isin(MODE_CLASSES)).sum()
        )
    if "split" in frame.columns:
        summary["split_distribution"] = {
            str(label): int(count)
            for label, count in frame["split"].astype("string").value_counts(dropna=False).items()
        }
    if "commute_direction" in frame.columns:
        summary["commute_direction_distribution"] = {
            str(label): int(count)
            for label, count in frame["commute_direction"]
            .astype("string")
            .value_counts(dropna=False)
            .items()
        }
    summary["missing_rate"] = {
        column: float(frame[column].isna().mean()) if row_count else 0.0
        for column in MODEL_FEATURES
        if column in frame.columns
    }
    return summary


def summarize_csv(path: str | PathLike[str], *, chunksize: int = 50_000) -> dict[str, object]:
    """CSV를 chunk 단위로 읽어 전체 요약을 계산한다."""

    if chunksize <= 0:
        raise ValueError("chunksize는 1 이상이어야 합니다")
    class_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    commute_counts: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()
    row_count = 0
    for chunk in pd.read_csv(path, encoding="utf-8-sig", chunksize=chunksize):
        row_count += len(chunk)
        if "actual_mode" in chunk:
            class_counts.update(chunk["actual_mode"].astype("string").fillna("<NA>").astype(str))
        if "split" in chunk:
            split_counts.update(chunk["split"].astype("string").fillna("<NA>").astype(str))
        if "commute_direction" in chunk:
            commute_counts.update(
                chunk["commute_direction"].astype("string").fillna("<NA>").astype(str)
            )
        for column in MODEL_FEATURES:
            if column in chunk:
                missing_counts[column] += int(chunk[column].isna().sum())

    summary: dict[str, object] = {
        "row_count": row_count,
        "class_distribution": dict(class_counts),
        "split_distribution": dict(split_counts),
        "commute_direction_distribution": dict(commute_counts),
        "missing_rate": {
            column: missing_counts[column] / row_count if row_count else 0.0
            for column in MODEL_FEATURES
            if missing_counts[column] or row_count
        },
    }
    summary["unsupported_mode_count"] = sum(
        count for label, count in class_counts.items() if label not in MODE_CLASSES
    )
    return summary


def write_summary(summary: dict[str, object], path: str | PathLike[str]) -> None:
    """요약 지표를 정렬된 UTF-8 JSON으로 저장한다."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
