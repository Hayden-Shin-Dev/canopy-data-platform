from src.aihub.stage_evaluation import _metrics


def test_stage_metrics_keep_all_five_modes_in_report() -> None:
    modes = ["walk", "bike", "car", "bus", "rail"]

    result = _metrics(modes, modes)

    assert result["accuracy"] == 1
    assert result["macro_f1"] == 1
    assert result["confusion_matrix"] == [
        [1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1],
    ]
