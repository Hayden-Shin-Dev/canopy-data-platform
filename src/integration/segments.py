"""Temporal mode smoothing and trip segment assembly for integration output."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def smooth_window_modes(
    records: Sequence[Mapping[str, object]],
    *,
    minimum_context_score: float,
    minimum_ml_confidence: float,
) -> list[str]:
    """Keep ordered transit evidence through adjacent windows without labels."""

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
            if same_line and context_score >= minimum_context_score and sequence >= 0.5 and ml_mode != "walk":
                output.append("rail")
                continue
            rail_active = False
            active_line = None
        output.append(base_mode)
    return output
