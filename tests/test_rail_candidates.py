from src.evaluation.rail_candidates import replay_candidate


def _journey():
    return {
        "traces": [
            {"raw_mode": "walk", "final_mode": "rail", "subway_context_score": 0.45, "matched_subway_line": "5"},
            {"raw_mode": "rail", "final_mode": "rail", "subway_context_score": 0.80, "matched_subway_line": "5"},
        ]
    }


def test_strict_candidate_falls_back_to_raw_without_score():
    assert replay_candidate(_journey(), "A_strict_score") == ["walk", "rail"]


def test_consecutive_candidate_requires_same_line_neighbor():
    assert replay_candidate(_journey(), "B_consecutive_score") == ["walk", "rail"]


def test_unknown_candidate_is_rejected():
    try:
        replay_candidate(_journey(), "unknown")
    except ValueError as error:
        assert "unknown rail candidate" in str(error)
    else:
        raise AssertionError("unknown candidate should fail")
