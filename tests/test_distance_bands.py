from __future__ import annotations

import pandas as pd
import pytest

from src.ktdb.distance import add_distance_band, derive_distance_band


def test_derive_distance_band_uses_half_open_boundaries() -> None:
    assert derive_distance_band(0) == "under_1km"
    assert derive_distance_band(1) == "1_to_3km"
    assert derive_distance_band(3) == "3_to_5km"
    assert derive_distance_band(20) == "20km_or_more"
    assert pd.isna(derive_distance_band(pd.NA))


def test_add_distance_band_rejects_negative_distance() -> None:
    with pytest.raises(ValueError, match="음수"):
        add_distance_band(pd.DataFrame({"od_straight_distance_km": [-1.0]}))
