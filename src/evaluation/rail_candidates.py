"""Evaluation-only rail confirmation candidates.

These functions replay stored Production traces.  They do not run during
inference and are used to choose a candidate before changing the resolver.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def _score(trace: Mapping[str, Any]) -> float:
    return float(trace.get("subway_context_score") or 0.0)


def _candidate_mode(traces: Sequence[Mapping[str, Any]], index: int, strategy: str) -> str:
    trace = traces[index]
    raw = str(trace.get("raw_mode", ""))
    final = str(trace.get("final_mode", ""))
    if strategy == "baseline" or final != "rail" or raw == "rail":
        return final
    if strategy == "A_strict_score":
        return final if _score(trace) >= 0.70 else raw
    if strategy == "B_consecutive_score":
        line = trace.get("matched_subway_line")
        adjacent = []
        if index > 0:
            adjacent.append(traces[index - 1])
        if index + 1 < len(traces):
            adjacent.append(traces[index + 1])
        confirmed = _score(trace) >= 0.55 and any(
            _score(item) >= 0.55 and item.get("matched_subway_line") == line for item in adjacent
        )
        return final if confirmed else raw
    if strategy == "C_high_score":
        return final if _score(trace) >= 0.80 else raw
    raise ValueError(f"unknown rail candidate: {strategy}")


def replay_candidate(journey: Mapping[str, Any], strategy: str) -> list[str]:
    traces = journey.get("traces") or []
    return [_candidate_mode(traces, index, strategy) for index in range(len(traces))]
