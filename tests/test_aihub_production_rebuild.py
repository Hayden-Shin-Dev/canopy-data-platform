from pathlib import Path


def test_production_rebuild_uses_raw_duration_builder_not_feature_aggregation() -> None:
    script = (Path(__file__).resolve().parents[1] / "scripts/rebuild_aihub_production.ps1").read_text(encoding="utf-8")

    assert "scripts.build_aihub_duration_windows" in script
    assert "scripts.aggregate_aihub_windows" not in script
    assert "--feature-set robust" in script
