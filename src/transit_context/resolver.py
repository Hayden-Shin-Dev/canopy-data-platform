"""Combine existing GeoLife probabilities with transit evidence conservatively."""

from __future__ import annotations

from collections.abc import Mapping

from src.geolife.mode_mapping import CANOPY_MODES

from .settings import TransitSettings, load_settings


def resolve_mode(
    probabilities: Mapping[str, float],
    *,
    context: Mapping[str, object] | None = None,
    settings: TransitSettings | None = None,
) -> dict[str, object]:
    """Return an auditable decision without allowing proximity alone to force a mode."""

    settings = settings or load_settings()
    context = context or {}
    probs = {mode: max(0.0, float(probabilities.get(mode, 0.0))) for mode in CANOPY_MODES}
    total = sum(probs.values())
    if total <= 0:
        raise ValueError("mode probability 합계가 0보다 커야 합니다")
    probs = {mode: value / total for mode, value in probs.items()}
    ml_mode = max(CANOPY_MODES, key=probs.get)
    ml_confidence = probs[ml_mode]
    bus_score = float(context.get("bus_context_score", 0.0) or 0.0)
    subway_score = float(context.get("subway_context_score", 0.0) or 0.0)
    train_score = float(context.get("train_context_score", 0.0) or 0.0)
    rail_score = max(subway_score, train_score)
    strong = settings.resolver["strong_context_score"]
    minimum = settings.resolver["minimum_context_score"]
    margin = settings.resolver["ambiguity_margin"]
    candidates = {"bus": bus_score, "rail": rail_score}
    evidence_mode, evidence_score = max(candidates.items(), key=lambda item: item[1])
    subway_sequence = float(context.get("subway_sequence_score", 0.0) or 0.0)
    subway_line = float(context.get("subway_line_score", 0.0) or 0.0)
    subway_station_count = int(context.get("subway_observed_station_count", 0) or 0)
    structured_subway = (
        subway_station_count >= 2
        and subway_line >= 1.0
        and subway_sequence >= 0.5
        and subway_score >= minimum
    )
    final_mode = ml_mode
    correction_applied = False
    correction_reason = "ML prediction retained"
    decision_status = "unchanged"
    rail_subtype = None

    rail_has_structured_evidence = structured_subway or train_score >= strong
    bus_stateful = settings.resolver.get("bus_stateful_enabled", 0) >= 1
    bus_confirmed = context.get("bus_state") == "BUS_CONFIRMED"
    if ml_mode == "rail" and not rail_has_structured_evidence:
        # Station proximity alone is not enough to turn a high-speed car/bus
        # window into rail. Keep rail only when ordered subway evidence or a
        # strong KORAIL context is present.
        non_rail_modes = {mode: value for mode, value in probs.items() if mode != "rail"}
        strongest_non_rail = max(non_rail_modes, key=non_rail_modes.get)
        if bus_score >= minimum and bus_score > non_rail_modes[strongest_non_rail] + margin and (not bus_stateful or bus_confirmed):
            final_mode = "bus"
        else:
            final_mode = strongest_non_rail
        correction_applied = final_mode != ml_mode
        decision_status = "insufficient_context"
        correction_reason = "rail prediction requires structured transit evidence"
    elif structured_subway and probs["rail"] < probs[ml_mode] + margin:
        final_mode = "rail"
        correction_applied = final_mode != ml_mode
        decision_status = "corrected" if correction_applied else "confirmed"
        correction_reason = "trajectory showed ordered stations on one subway line"
    elif evidence_score >= strong and evidence_score > probs[evidence_mode] + margin and (not bus_stateful or evidence_mode != "bus" or bus_confirmed):
        final_mode = evidence_mode
        correction_applied = final_mode != ml_mode
        decision_status = "corrected" if correction_applied else "confirmed"
        correction_reason = f"strong {evidence_mode} context exceeded ML probability"
    elif evidence_score >= minimum and abs(bus_score - rail_score) < margin and evidence_score > minimum:
        decision_status = "ambiguous"
        correction_reason = "bus and rail context scores are close"
    elif ml_confidence < settings.resolver["minimum_ml_confidence"] and evidence_score < minimum:
        decision_status = "insufficient_context"
        correction_reason = "ML confidence and transit evidence are both low"

    # A non-rail model prediction must not be promoted to rail on a marginal
    # station/trajectory score.  The threshold is versioned in transit config.
    rail_confirmation_score = settings.resolver.get("rail_confirmation_score", strong)
    if final_mode == "rail" and ml_mode != "rail" and rail_score < rail_confirmation_score:
        non_rail_modes = {mode: value for mode, value in probs.items() if mode != "rail"}
        final_mode = max(non_rail_modes, key=non_rail_modes.get)
        correction_applied = True
        decision_status = "insufficient_context"
        correction_reason = "non-rail prediction requires stronger rail confirmation"

    if final_mode == "rail":
        if train_score > subway_score and train_score >= strong:
            rail_subtype = "train"
        elif subway_score >= strong:
            rail_subtype = "subway"
        else:
            rail_subtype = "unknown"
    return {
        "ml_predicted_mode": ml_mode,
        "ml_confidence": ml_confidence,
        **{f"{mode}_probability": probs[mode] for mode in CANOPY_MODES},
        "bus_context_score": min(1.0, max(0.0, bus_score)),
        "subway_context_score": min(1.0, max(0.0, subway_score)),
        "train_context_score": min(1.0, max(0.0, train_score)),
        "matched_bus_route_id": context.get("matched_bus_route_id"),
        "matched_bus_route_no": context.get("matched_bus_route_no"),
        "matched_subway_line": context.get("matched_subway_line"),
        "subway_start_station_id": context.get("subway_start_station_id"),
        "subway_end_station_id": context.get("subway_end_station_id"),
        "matched_train_start_station": context.get("matched_train_start_station"),
        "matched_train_end_station": context.get("matched_train_end_station"),
        "final_mode": final_mode,
        "rail_subtype": rail_subtype,
        "correction_applied": correction_applied,
        "decision_status": decision_status,
        "decision_confidence": max(probs[final_mode], evidence_score),
        "correction_reason": correction_reason,
    }
