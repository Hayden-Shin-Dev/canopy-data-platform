"""Reusable WGS84 nearest-neighbour index for transit references."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree


EARTH_RADIUS_M = 6_371_008.8


@dataclass
class GeoPointIndex:
    frame: pd.DataFrame
    _tree: BallTree

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "GeoPointIndex":
        required = {"latitude", "longitude"}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"공간 인덱스에 필요한 좌표 컬럼이 없습니다: {missing}")
        values = frame[["latitude", "longitude"]].apply(pd.to_numeric, errors="coerce")
        valid = values["latitude"].between(-90, 90) & values["longitude"].between(-180, 180)
        if not valid.all():
            raise ValueError("공간 인덱스 입력에 유효하지 않은 좌표가 있습니다")
        radians = np.radians(values.to_numpy(dtype=float))
        return cls(frame.reset_index(drop=True).copy(), BallTree(radians, metric="haversine"))

    def query(self, latitude: float, longitude: float, *, radius_m: float, limit: int | None = None) -> pd.DataFrame:
        if radius_m < 0:
            raise ValueError("검색 반경은 음수가 될 수 없습니다")
        point = np.radians(np.asarray([[float(latitude), float(longitude)]]))
        count = self._tree.query_radius(point, r=radius_m / EARTH_RADIUS_M, return_distance=True, sort_results=True)
        indices = count[0][0]
        distances = count[1][0] * EARTH_RADIUS_M
        if limit is not None:
            indices, distances = indices[:limit], distances[:limit]
        result = self.frame.iloc[indices].copy()
        result["distance_m"] = distances
        return result.reset_index(drop=True)

    def nearest(self, latitude: float, longitude: float) -> pd.Series:
        point = np.radians(np.asarray([[float(latitude), float(longitude)]]))
        distances, indices = self._tree.query(point, k=1)
        result = self.frame.iloc[int(indices[0, 0])].copy()
        result["distance_m"] = float(distances[0, 0] * EARTH_RADIUS_M)
        return result

    def nearest_many(self, coordinates: list[tuple[float, float]]) -> pd.DataFrame:
        """Return one nearest reference row per coordinate in input order."""

        if not coordinates:
            return self.frame.iloc[[]].assign(distance_m=pd.Series(dtype=float))
        points = np.radians(np.asarray(coordinates, dtype=float))
        distances, indices = self._tree.query(points, k=1)
        result = self.frame.iloc[indices[:, 0]].copy().reset_index(drop=True)
        result["distance_m"] = distances[:, 0] * EARTH_RADIUS_M
        return result
