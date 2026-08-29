"""Apply the evidence resolver to a window table with existing ML probabilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.geolife.mode_mapping import CANOPY_MODES

from .resolver import resolve_mode


PROBABILITY_COLUMNS = tuple(f"{mode}_probability" for mode in CANOPY_MODES)


def apply_resolver_to_frame(frame: pd.DataFrame, *, source_kind: str = "realtime") -> pd.DataFrame:
    """Resolve rows while refusing to attach Korean transit references to GeoLife."""

    if source_kind not in {"realtime", "reference", "geolife"}:
        raise ValueError("source_kind는 realtime, reference, geolife 중 하나여야 합니다")
    if source_kind == "geolife":
        raise ValueError("GeoLife는 한국 transit network와 결합하지 않습니다. realtime/reference 입력을 사용하세요")
    missing = sorted(set(PROBABILITY_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"ML probability 컬럼이 없습니다: {missing}")
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        context = {key: row[key] for key in ("bus_context_score", "subway_context_score", "train_context_score", "matched_bus_route_id", "matched_bus_route_no", "matched_subway_line", "subway_start_station_id", "subway_end_station_id", "matched_train_start_station", "matched_train_end_station") if key in row and pd.notna(row[key])}
        result = resolve_mode({mode: row[f"{mode}_probability"] for mode in CANOPY_MODES}, context=context)
        output = row.to_dict()
        output.update(result)
        rows.append(output)
    return pd.DataFrame(rows, index=frame.index)


def apply_resolver_to_csv(input_csv: str | Path, output_csv: str | Path, *, source_kind: str = "realtime") -> dict[str, object]:
    frame = pd.read_csv(input_csv, encoding="utf-8-sig")
    result = apply_resolver_to_frame(frame, source_kind=source_kind)
    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False, encoding="utf-8-sig")
    return {"input_csv": str(input_csv), "output_csv": str(output), "source_kind": source_kind, "row_count": int(len(result)), "status_counts": result["decision_status"].value_counts().sort_index().to_dict()}
