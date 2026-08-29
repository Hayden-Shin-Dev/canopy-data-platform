from src.evaluation.root_cause import (
    correctness_transitions,
    hybrid_interventions,
    multimodal_failures,
    per_mode_correctness,
    raw_final_transition_matrix,
    transit_error_counts,
)


def _journeys():
    return [
        {
            "trip_id": "a",
            "scenario_category": "walk",
            "labels": ["walk", "walk"],
            "raw_modes": ["walk", "walk"],
            "final_modes": ["walk", "rail"],
        },
        {
            "trip_id": "b",
            "scenario_category": "walk_rail_walk",
            "labels": ["walk", "rail", "walk"],
            "raw_modes": ["walk", "walk", "walk"],
            "final_modes": ["walk", "rail", "walk"],
        },
    ]


def test_transition_and_correctness_counts():
    journeys = _journeys()
    matrix = raw_final_transition_matrix(journeys)
    assert matrix["walk"]["walk"] == 3
    assert matrix["walk"]["rail"] == 2
    counts = correctness_transitions(journeys)
    assert counts["KEPT_CORRECT"] == 3
    assert counts["BROKEN_BY_FINAL"] == 1
    assert counts["FIXED_BY_FINAL"] == 1


def test_mode_and_transit_aggregations():
    journeys = _journeys()
    per_mode = per_mode_correctness(journeys)
    assert per_mode["walk"]["kept_correct"] == 3
    assert per_mode["walk"]["broken_by_final"] == 1
    interventions = hybrid_interventions(journeys)
    assert interventions["total"] == 2
    assert interventions["helpful"] == 1
    assert interventions["harmful"] == 1
    errors = transit_error_counts(journeys)
    assert errors["false_rail"] == 1


def test_multimodal_failure_classification():
    rows = multimodal_failures(_journeys())
    assert rows == [
        {
            "trip_id": "b",
            "ground_truth_sequence": "walk->rail->walk",
            "raw_sequence": "walk",
            "final_sequence": "walk->rail->walk",
            "failure_type": "MATCH",
        }
    ]
