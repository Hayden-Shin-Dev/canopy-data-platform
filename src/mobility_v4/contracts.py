"""Explicit contract for the official AI-Hub multimodal checkpoint.

This module deliberately does not synthesize missing sensors or map unknown
official labels to Canopy classes. It is a guardrail for the experimental V4
path, not a replacement for the production GPS-only runtime.
"""

from __future__ import annotations

from collections.abc import Mapping

REQUIRED_MODALITIES = ("gps", "imu", "ap", "bts")
OFFICIAL_CONTRACT = {
    "input_channels": 340,
    "timesteps": 60,
    "output_classes": 11,
    "modalities": REQUIRED_MODALITIES,
    # Official preprocessing aggregates GPS/BTS in 5-second bins and repeats
    # one minute (PER_SECTION=1, PER_MIN=60) over 60 timesteps.
    "observation_duration_seconds": 60,
    "label_mapping_status": "unverified",
}


def validate_sample(sample: Mapping[str, object]) -> dict[str, object]:
    """Validate presence and shape of a full-modality sample.

    Missing modality data is rejected instead of being replaced by zeros or
    another synthetic value. ``tensor_shape`` must be ``(340, 60)`` when a
    preprocessed tensor is supplied.
    """

    missing = [name for name in REQUIRED_MODALITIES if not sample.get(name)]
    result: dict[str, object] = {"valid": not missing, "missing_modalities": missing}
    shape = sample.get("tensor_shape")
    if shape is not None:
        normalized = tuple(shape) if isinstance(shape, (tuple, list)) else None
        result["tensor_shape"] = list(normalized) if normalized else shape
        if normalized != (340, 60):
            result["valid"] = False
            result["shape_error"] = "expected (340, 60)"
    return result
