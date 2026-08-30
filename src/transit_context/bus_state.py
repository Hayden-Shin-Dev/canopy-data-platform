"""Stateful accumulation for Bus Context evidence across GPS windows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class BusEvidenceState:
    state: str = "UNKNOWN"
    score: float = 0.0
    positive_windows: int = 0
    weak_windows: int = 0


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def update_bus_state(
    previous: BusEvidenceState,
    context: Mapping[str, object],
    *,
    raw_mode: str,
    decay: float = 0.80,
    candidate_score: float = 0.35,
    probable_score: float = 0.50,
    confirmed_score: float = 0.65,
    release_score: float = 0.25,
) -> BusEvidenceState:
    """Accumulate independent window signals with hysteresis and release."""

    signal_values = [
        float(context.get("bus_stop_proximity_score", 0.0) or 0.0),
        float(context.get("bus_route_match_score", 0.0) or 0.0),
        float(context.get("bus_sequence_score", 0.0) or 0.0),
        1.0 if context.get("direction_consistent") else 0.0,
        1.0 if context.get("temporal_consistent") else 0.0,
        1.0 if raw_mode == "bus" else 0.0,
    ]
    current = _bounded(sum(signal_values) / len(signal_values))
    accumulated = current if previous.score == 0.0 else _bounded(previous.score * decay + current * (1.0 - decay))
    positive = previous.positive_windows + (1 if current >= candidate_score else 0)
    weak = previous.weak_windows + (1 if current < release_score else 0)
    if accumulated >= confirmed_score and positive >= 2:
        state = "BUS_CONFIRMED"
        weak = 0
    elif accumulated >= probable_score and positive >= 1:
        state = "BUS_PROBABLE"
    elif accumulated >= candidate_score:
        state = "BUS_CANDIDATE"
    elif weak >= 2:
        state = "UNKNOWN"
        accumulated = _bounded(accumulated * 0.5)
        positive = 0
        weak = 0
    else:
        state = previous.state if previous.state != "UNKNOWN" else "UNKNOWN"
    return BusEvidenceState(state=state, score=accumulated, positive_windows=positive, weak_windows=weak)
