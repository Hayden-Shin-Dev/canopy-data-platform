"""Build a KTDB model input from the supplied route and local reference data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

import pandas as pd
from pyproj import Transformer

from src.config import DISTANCE_BANDS, PROJECT_ROOT
from src.integration.distance import trajectory_distance_km
from src.integration.gps_contract import GpsEvent
from src.ktdb.distance import derive_distance_band, transform_to_wgs84
from src.ktdb.schema import MODEL_FEATURES


DEFAULT_DATASET = PROJECT_ROOT / "data/processed/population_baseline/ktdb/01_population_model_training_all.csv"
DEFAULT_CENTROIDS = PROJECT_ROOT / "data/reference/admin_dong_centroids_2021.csv"
DEFAULT_MAPPING = PROJECT_ROOT / "data/reference/ktdb_sgis_admin_dong_mapping_2021.csv"


@dataclass(frozen=True)
class KtdbScenario:
    """Model features plus the references used to derive each value."""

    features: dict[str, object]
    provenance: dict[str, object]


def _code_text(value: object) -> str:
    """Keep numeric administrative codes stable when pandas reads them as floats."""

    if pd.isna(value):
        return ""
    text = str(value).strip()
    try:
        number = float(text)
    except ValueError:
        return text
    return str(int(number)) if number.is_integer() else text


def _nearest_centroid(latitude: float, longitude: float, centroids: pd.DataFrame) -> pd.Series:
    required = {"adm_cd", "adm_nm", "x", "y", "source_crs"}
    missing = sorted(required - set(centroids.columns))
    if missing:
        raise ValueError(f"centroid reference columns missing: {missing}")
    source_crs = str(centroids["source_crs"].dropna().iloc[0])
    if centroids["source_crs"].dropna().astype(str).nunique() != 1:
        raise ValueError("centroid reference must use one source CRS")
    x, y = Transformer.from_crs("EPSG:4326", source_crs, always_xy=True).transform(longitude, latitude)
    numeric = centroids[["x", "y"]].apply(pd.to_numeric, errors="coerce")
    valid = numeric.notna().all(axis=1)
    if not valid.any():
        raise ValueError("centroid reference has no usable coordinates")
    distance = ((numeric.loc[valid, "x"] - x) ** 2 + (numeric.loc[valid, "y"] - y) ** 2) ** 0.5
    return centroids.loc[distance.idxmin()].copy()


def _ktdb_admin_row(sgis_code: object, mapping: pd.DataFrame) -> pd.Series:
    required = {"ktdb_admin_code", "ktdb_full_name", "sgis_adm_cd"}
    missing = sorted(required - set(mapping.columns))
    if missing:
        raise ValueError(f"KTDB to SGIS mapping columns missing: {missing}")
    target = _code_text(sgis_code)
    rows = mapping[mapping["sgis_adm_cd"].map(_code_text).eq(target)]
    if len(rows) != 1:
        raise ValueError(f"SGIS centroid {sgis_code!r} has {len(rows)} KTDB mappings")
    return rows.iloc[0]


def _parts(full_name: object) -> tuple[str, str]:
    values = str(full_name).split()
    if len(values) < 2:
        raise ValueError(f"KTDB full admin name is incomplete: {full_name!r}")
    return values[0], values[1]


def build_expected_features(
    events: Sequence[GpsEvent],
    *,
    purpose: str | None = None,
    commute_direction: str = "to_work",
    dataset_path: str | Path = DEFAULT_DATASET,
    centroids_path: str | Path = DEFAULT_CENTROIDS,
    mapping_path: str | Path = DEFAULT_MAPPING,
) -> KtdbScenario:
    """Derive all model features from event time, route coordinates and references.

    The commute purpose is taken from existing KTDB rows marked ``to_work`` when
    it is not supplied explicitly. No ground-truth mode or synthetic value is read.
    """

    if len(events) < 2:
        raise ValueError("at least two GPS events are required")
    centroids = pd.read_csv(centroids_path, encoding="utf-8-sig")
    mapping = pd.read_csv(mapping_path, encoding="utf-8-sig")
    origin_centroid = _nearest_centroid(events[0].latitude, events[0].longitude, centroids)
    destination_centroid = _nearest_centroid(events[-1].latitude, events[-1].longitude, centroids)
    origin = _ktdb_admin_row(origin_centroid["adm_cd"], mapping)
    destination = _ktdb_admin_row(destination_centroid["adm_cd"], mapping)
    origin_code = str(origin["ktdb_admin_code"])
    destination_code = str(destination["ktdb_admin_code"])
    origin_sido, origin_sigungu = _parts(origin["ktdb_full_name"])
    destination_sido, destination_sigungu = _parts(destination["ktdb_full_name"])

    origin_lon, origin_lat = transform_to_wgs84(origin_centroid["x"], origin_centroid["y"], source_crs=str(origin_centroid["source_crs"]))
    destination_lon, destination_lat = transform_to_wgs84(destination_centroid["x"], destination_centroid["y"], source_crs=str(destination_centroid["source_crs"]))
    from src.common.geo import haversine_distance_km

    distance_km = haversine_distance_km(origin_lat, origin_lon, destination_lat, destination_lon)
    local_time = events[0].timestamp.astimezone(ZoneInfo("Asia/Seoul"))
    purpose_source = "explicit"
    if purpose is None:
        dataset = pd.read_csv(dataset_path, usecols=["purpose", "commute_direction"], encoding="utf-8-sig")
        candidates = dataset.loc[dataset["commute_direction"].eq(commute_direction), "purpose"].dropna().astype(str)
        if candidates.empty:
            raise ValueError(f"no KTDB purpose reference for commute_direction={commute_direction!r}")
        purpose = str(candidates.mode().iloc[0])
        purpose_source = "KTDB rows with commute_direction=to_work"

    od_scope = "inter_sido"
    if origin_code == destination_code:
        od_scope = "same_dong"
    elif origin_sido == destination_sido:
        od_scope = "same_sigungu" if origin_sigungu == destination_sigungu else "same_sido"
    features: dict[str, object] = {
        "weekday": local_time.strftime("%a"),
        "departure_hour": local_time.hour,
        "departure_minute_bin": (local_time.minute // 15) * 15,
        "time_band": "morning_peak" if 7 <= local_time.hour < 10 else "daytime" if 10 <= local_time.hour < 17 else "evening_peak" if 17 <= local_time.hour < 20 else "night" if 20 <= local_time.hour < 24 else "early_morning" if 4 <= local_time.hour < 7 else "late_night",
        "origin_admin_dong": origin_code,
        "origin_x": float(origin_centroid["x"]),
        "origin_y": float(origin_centroid["y"]),
        "origin_sido": origin_sido,
        "origin_sigungu": origin_sigungu,
        "destination_admin_dong": destination_code,
        "destination_x": float(destination_centroid["x"]),
        "destination_y": float(destination_centroid["y"]),
        "destination_sido": destination_sido,
        "destination_sigungu": destination_sigungu,
        "od_scope": od_scope,
        "od_straight_distance_km": distance_km,
        "distance_band": derive_distance_band(distance_km, bands=DISTANCE_BANDS),
        "purpose": purpose,
        "commute_direction": commute_direction,
    }
    if set(features) != set(MODEL_FEATURES):
        raise AssertionError("KTDB scenario feature contract drifted")
    return KtdbScenario(
        features=features,
        provenance={
            "origin_sgis_adm_cd": str(origin_centroid["adm_cd"]),
            "destination_sgis_adm_cd": str(destination_centroid["adm_cd"]),
            "origin_ktdb_admin_code": origin_code,
            "destination_ktdb_admin_code": destination_code,
            "origin_centroid_distance_source": str(origin_centroid["source_crs"]),
            "destination_centroid_distance_source": str(destination_centroid["source_crs"]),
            "route_distance_km": trajectory_distance_km(events),
            "purpose_source": purpose_source,
        },
    )
