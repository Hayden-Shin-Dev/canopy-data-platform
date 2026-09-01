from pathlib import Path

from src.integration import model_config


def test_default_model_honours_explicit_environment_path(monkeypatch, tmp_path: Path) -> None:
    configured = tmp_path / "custom.joblib"
    monkeypatch.setenv("CANOPY_MOBILITY_MODEL", str(configured))
    assert model_config.default_mobility_model() == configured


def test_default_model_prefers_aihub_artifact_when_available(monkeypatch, tmp_path: Path) -> None:
    aihub = tmp_path / "aihub.joblib"
    legacy = tmp_path / "legacy.joblib"
    aihub.write_bytes(b"model")
    monkeypatch.delenv("CANOPY_MOBILITY_MODEL", raising=False)
    monkeypatch.setattr(model_config, "AIHUB_PRODUCTION_MODEL", aihub)
    monkeypatch.setattr(model_config, "LEGACY_MODEL", legacy)
    assert model_config.default_mobility_model() == aihub


def test_default_model_falls_back_to_legacy_artifact(monkeypatch, tmp_path: Path) -> None:
    aihub = tmp_path / "missing-aihub.joblib"
    legacy = tmp_path / "legacy.joblib"
    legacy.write_bytes(b"model")
    monkeypatch.delenv("CANOPY_MOBILITY_MODEL", raising=False)
    monkeypatch.setattr(model_config, "AIHUB_PRODUCTION_MODEL", aihub)
    monkeypatch.setattr(model_config, "LEGACY_MODEL", legacy)
    assert model_config.default_mobility_model() == legacy
