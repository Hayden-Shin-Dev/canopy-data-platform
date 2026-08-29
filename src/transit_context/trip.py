"""Aggregate adjacent window evidence into a trip-level context."""

from __future__ import annotations

import pandas as pd


def build_trip_context(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize consecutive windows without changing their individual decisions."""

    required = {"window_start", "bus_context_score", "subway_context_score", "train_context_score"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Trip Context에 필요한 컬럼이 없습니다: {missing}")
    result = frame.copy()
    if "trip_id" not in result.columns:
        if {"user_id", "trajectory_id"} <= set(result.columns):
            result["trip_id"] = result["user_id"].astype(str) + ":" + result["trajectory_id"].astype(str)
        else:
            raise ValueError("trip_id 또는 user_id/trajectory_id가 필요합니다")
    result["window_start"] = pd.to_datetime(result["window_start"], errors="raise")
    result.sort_values(["trip_id", "window_start"], inplace=True)
    groups = result.groupby("trip_id", sort=False)
    summary = groups.agg(
        window_count=("trip_id", "size"),
        trip_start=("window_start", "min"),
        trip_end=("window_start", "max"),
        bus_context_score=("bus_context_score", "max"),
        subway_context_score=("subway_context_score", "max"),
        train_context_score=("train_context_score", "max"),
    ).reset_index()
    summary["trip_duration_sec"] = (summary["trip_end"] - summary["trip_start"]).dt.total_seconds()
    summary["transit_context_score"] = summary[["bus_context_score", "subway_context_score", "train_context_score"]].max(axis=1)
    summary["trip_context_status"] = summary["transit_context_score"].map(lambda value: "supported" if value >= 0.7 else "weak_or_missing")
    return summary
