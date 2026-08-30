from src.transit_context.bus_state import BusEvidenceState, update_bus_state


def _context(**values):
    return {
        "bus_stop_proximity_score": 1.0,
        "bus_route_match_score": 1.0,
        "bus_sequence_score": 1.0,
        "direction_consistent": True,
        "temporal_consistent": True,
        **values,
    }


def test_state_requires_accumulated_windows_before_confirmation() -> None:
    state = BusEvidenceState()
    state = update_bus_state(state, _context(), raw_mode="car")
    assert state.state in {"BUS_CANDIDATE", "BUS_PROBABLE"}
    assert state.state != "BUS_CONFIRMED"
    state = update_bus_state(state, _context(), raw_mode="bus")
    assert state.state == "BUS_CONFIRMED"


def test_state_releases_after_consecutive_weak_windows() -> None:
    state = BusEvidenceState(state="BUS_CONFIRMED", score=0.9, positive_windows=3)
    weak = {"bus_stop_proximity_score": 0.0, "bus_route_match_score": 0.0, "bus_sequence_score": 0.0}
    state = update_bus_state(state, weak, raw_mode="walk", decay=0.1)
    state = update_bus_state(state, weak, raw_mode="walk", decay=0.1)
    assert state.state == "UNKNOWN"

