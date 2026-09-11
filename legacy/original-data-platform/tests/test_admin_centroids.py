from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ktdb.admin_centroids import (
    SGIS_SOURCE_CRS,
    collect_admin_dong_centroids,
    load_or_collect_centroids,
    write_centroid_reference,
)
from src.ktdb.sgis import SgisApiError


def _boundary_feature(adm_cd: str, adm_nm: str, x: object = 1, y: object = 2) -> dict[str, object]:
    properties = {"adm_cd": adm_cd, "adm_nm": adm_nm, "x": x, "y": y}
    return {"type": "Feature", "properties": properties, "geometry": {"type": "Polygon"}}


class FakeSgisClient:
    def __init__(self, *, missing_dong_xy: bool = False) -> None:
        self.calls: list[str | None] = []
        dong = _boundary_feature("1101053", "서울특별시 종로구 사직동", 953808.5, 1952441.25)
        if missing_dong_xy:
            dong["properties"].pop("x")  # type: ignore[union-attr]
        self.responses = {
            None: {"errCd": 0, "features": [_boundary_feature("11", "서울특별시")]},
            "11": {"errCd": 0, "features": [_boundary_feature("11010", "서울특별시 종로구")]},
            "11010": {"errCd": 0, "features": [dong]},
        }

    def request_boundary(
        self, *, adm_cd: str | None, low_search: int, year: str
    ) -> dict[str, object]:
        assert low_search == 1
        assert year == "2021"
        self.calls.append(adm_cd)
        return self.responses[adm_cd]


def test_collect_admin_dong_centroids_follows_all_levels(tmp_path: Path) -> None:
    client = FakeSgisClient()

    result = collect_admin_dong_centroids(client, raw_response_dir=tmp_path)  # type: ignore[arg-type]

    assert client.calls == [None, "11", "11010"]
    assert result.loc[0, "adm_cd"] == "1101053"
    assert result.loc[0, "source_crs"] == SGIS_SOURCE_CRS
    assert result.loc[0, "x"] == pytest.approx(953808.5)
    assert {path.name for path in tmp_path.glob("*.geojson")} == {
        "national.geojson",
        "11.geojson",
        "11010.geojson",
    }


def test_collect_admin_dong_centroids_rejects_missing_representative_xy(tmp_path: Path) -> None:
    client = FakeSgisClient(missing_dong_xy=True)

    with pytest.raises(SgisApiError, match="polygon 좌표로 대체하지 않습니다"):
        collect_admin_dong_centroids(client, raw_response_dir=tmp_path)  # type: ignore[arg-type]


def test_load_or_collect_centroids_reuses_existing_csv(tmp_path: Path) -> None:
    path = tmp_path / "centroids.csv"
    expected = pd.DataFrame(
        {
            "adm_cd": ["1101053"],
            "adm_nm": ["서울특별시 종로구 사직동"],
            "x": [953808.5],
            "y": [1952441.25],
            "source_crs": [SGIS_SOURCE_CRS],
            "reference_year": ["2021"],
        }
    )
    write_centroid_reference(expected, path)

    result = load_or_collect_centroids(path, client=None, raw_response_dir=tmp_path / "raw")

    assert result.loc[0, "adm_cd"] == "1101053"
    assert result.loc[0, "x"] == pytest.approx(953808.5)
