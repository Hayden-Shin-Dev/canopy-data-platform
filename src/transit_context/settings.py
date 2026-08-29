"""Load Transit Context thresholds and weights from versioned configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT


DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "transit_context.json"


@dataclass(frozen=True)
class TransitSettings:
    version: str
    coordinate_system: str
    radii_m: dict[str, float]
    weights: dict[str, float]
    resolver: dict[str, float]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "TransitSettings":
        required = {"version", "coordinate_system", "radii_m", "weights", "resolver"}
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"Transit Context 설정에 필요한 항목이 없습니다: {missing}")
        radii = {str(k): float(v) for k, v in data["radii_m"].items()}
        weights = {str(k): float(v) for k, v in data["weights"].items()}
        resolver = {str(k): float(v) for k, v in data["resolver"].items()}
        if any(value <= 0 for value in radii.values()):
            raise ValueError("Transit Context 반경은 0보다 커야 합니다")
        if any(value < 0 for value in weights.values()):
            raise ValueError("Transit Context 가중치는 음수가 될 수 없습니다")
        return cls(str(data["version"]), str(data["coordinate_system"]), radii, weights, resolver)


def load_settings(path: str | Path = DEFAULT_CONFIG_PATH) -> TransitSettings:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Transit Context 설정은 JSON 객체여야 합니다")
    return TransitSettings.from_mapping(data)
