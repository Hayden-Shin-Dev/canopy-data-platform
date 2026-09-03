"""Resolve the mobility model used by production entry points."""

from __future__ import annotations

import os
from pathlib import Path

from src.config import PROJECT_ROOT


LEGACY_MODEL = PROJECT_ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib"
AIHUB_PRODUCTION_MODEL = PROJECT_ROOT / "models/mobility_recognition/aihub_canonical_raw120.joblib"
AIHUB_ROLLBACK_MODEL = PROJECT_ROOT / "models/mobility_recognition/aihub_hist120.joblib"


def default_mobility_model() -> Path:
    """Prefer the validated AI-Hub artifact, with an explicit rollback path."""

    configured = os.environ.get("CANOPY_MOBILITY_MODEL")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_ROOT / path
    if AIHUB_PRODUCTION_MODEL.is_file():
        return AIHUB_PRODUCTION_MODEL
    if AIHUB_ROLLBACK_MODEL.is_file():
        return AIHUB_ROLLBACK_MODEL
    return LEGACY_MODEL
