from scripts.evaluate_transit_fusion import LABELS, _majority


def test_transit_fusion_evaluation_keeps_fixture_labels_out_of_inference() -> None:
    assert LABELS["seoul_bus_route.csv"] == "bus"
    assert _majority(["walk", "rail", "rail"]) == "rail"
    assert _majority([]) is None
