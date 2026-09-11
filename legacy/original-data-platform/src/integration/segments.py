"""Temporal mode smoothing and trip segment assembly for integration output."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def smooth_window_modes(
    records: Sequence[Mapping[str, object]],
    *,
    minimum_context_score: float,
    minimum_ml_confidence: float,
    pre_transit_bike_max_windows: int = 2,
    pre_transit_bike_max_confidence: float = 0.75,
) -> list[str]:
    """Keep ordered transit evidence and remove short pre-transit bike spikes.

    The correction only uses causal model output and structured station evidence.
    It is intentionally limited to a short, low-confidence bike run immediately
    before an evidence-backed rail run; a sustained bike trip remains unchanged.
    """

    output: list[str] = []
    active_line: str | None = None
    rail_active = False
    for record in records:
        decision = record["decision"]
        context = record["transit_context"]
        base_mode = str(decision["final_mode"])
        window = record.get("window")
        ml_mode = str(getattr(window, "predicted_mode", None) or decision.get("ml_predicted_mode") or base_mode)
        ml_confidence = float(getattr(window, "confidence", None) or decision.get("ml_confidence") or 0.0)
        line = context.get("matched_subway_line")
        context_score = float(context.get("subway_context_score") or 0.0)
        sequence = float(context.get("subway_sequence_score") or 0.0)
        if ml_mode == "walk" and ml_confidence >= minimum_ml_confidence:
            rail_active = False
            active_line = None
            output.append("walk")
            continue
        if base_mode == "rail" and not (rail_active and ml_mode == "walk" and ml_confidence >= minimum_ml_confidence):
            rail_active = True
            active_line = str(line) if line is not None else active_line
            output.append("rail")
            continue
        if rail_active:
            if ml_mode == "walk" and ml_confidence >= minimum_ml_confidence:
                rail_active = False
                active_line = None
                output.append(ml_mode)
                continue
            same_line = active_line is None or line is None or str(line) == active_line
            rail_continuity = (
                context_score >= minimum_context_score
                or (ml_mode == "rail" and ml_confidence >= minimum_ml_confidence * 0.75)
            )
            if same_line and rail_continuity and ml_mode == "rail":
                output.append("rail")
                continue
            rail_active = False
            active_line = None
        output.append(base_mode)
    if pre_transit_bike_max_windows < 1:
        return output

    # GPS windows near a station can briefly look like bike movement.  If the
    # next window establishes ordered rail evidence, treat that short spike as
    # part of the preceding mode instead of changing the trip's mode history.
    corrected = list(output)
    index = 0
    while index < len(output):
        if output[index] != "bike":
            index += 1
            continue
        run_start = index
        while index < len(output) and output[index] == "bike":
            index += 1
        run_end = index
        run_length = run_end - run_start
        if run_length > pre_transit_bike_max_windows or run_start == 0 or run_end >= len(output):
            continue
        if output[run_start - 1] == "bike" or output[run_end] != "rail":
            continue
        run_records = records[run_start:run_end]
        next_context = records[run_end].get("transit_context", {})
        has_no_ordered_evidence = all(
            float(record.get("transit_context", {}).get("subway_sequence_score") or 0.0) < 0.5
            for record in run_records
        )
        low_confidence = all(
            float(getattr(record.get("window"), "confidence", None) or record.get("decision", {}).get("ml_confidence") or 0.0)
            <= pre_transit_bike_max_confidence
            for record in run_records
        )
        rail_evidence = (
            float(next_context.get("subway_context_score") or 0.0) >= minimum_context_score
            and float(next_context.get("subway_sequence_score") or 0.0) >= 0.5
        )
        if has_no_ordered_evidence and low_confidence and rail_evidence:
            corrected[run_start:run_end] = [output[run_start - 1]] * run_length
    return corrected
