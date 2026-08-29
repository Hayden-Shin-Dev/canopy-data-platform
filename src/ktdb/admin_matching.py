"""KTDB 10자리 행정동 코드와 SGIS 7자리 코드를 이름으로 연결한다."""

from __future__ import annotations

from collections import Counter

import pandas as pd

from .admin_centroids import validate_centroid_reference


MAPPING_COLUMNS = (
    "ktdb_admin_code",
    "ktdb_full_name",
    "sgis_adm_cd",
    "sgis_adm_nm",
    "x",
    "y",
    "match_status",
    "candidate_count",
)


def _normalize_name(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def _full_admin_name(row: pd.Series) -> str:
    parts = [_normalize_name(row[column]) for column in ("sido", "sigungu", "admin_name")]
    return " ".join(part for part in parts if part)


def inspect_code_systems(admin_lookup: pd.DataFrame, centroids: pd.DataFrame) -> dict[str, object]:
    """실제 두 reference의 코드 길이와 직접 일치 여부를 수치로 남긴다."""

    ktdb_codes = admin_lookup["admin_code"].dropna().astype(str).map(str.strip)
    sgis_codes = centroids["adm_cd"].dropna().astype(str).map(str.strip)
    return {
        "ktdb_code_count": int(ktdb_codes.nunique()),
        "sgis_code_count": int(sgis_codes.nunique()),
        "ktdb_code_lengths": dict(sorted(Counter(ktdb_codes.map(len)).items())),
        "sgis_code_lengths": dict(sorted(Counter(sgis_codes.map(len)).items())),
        "direct_code_overlap": int(len(set(ktdb_codes) & set(sgis_codes))),
        "mapping_method": "exact_full_admin_name",
    }


def build_admin_centroid_mapping(
    admin_lookup: pd.DataFrame,
    centroids: pd.DataFrame,
) -> pd.DataFrame:
    """시도·시군구·행정동 전체 이름이 정확히 같은 경우만 연결한다."""

    required = {"admin_code", "sido", "sigungu", "admin_name"}
    missing = sorted(required - set(admin_lookup.columns))
    if missing:
        raise ValueError(f"KTDB 행정동 lookup에 필요한 컬럼이 없습니다: {missing}")
    validate_centroid_reference(centroids)

    ktdb = admin_lookup[list(required)].copy()
    ktdb["ktdb_admin_code"] = ktdb["admin_code"].astype("string").fillna("").str.strip()
    ktdb["ktdb_full_name"] = ktdb.apply(_full_admin_name, axis=1)

    sgis = centroids[["adm_cd", "adm_nm", "x", "y"]].copy()
    sgis["_normalized_name"] = sgis["adm_nm"].map(_normalize_name)
    candidate_counts = sgis.groupby("_normalized_name", dropna=False)["adm_cd"].size()
    unique_sgis = sgis[sgis["_normalized_name"].map(candidate_counts).eq(1)].set_index("_normalized_name")

    normalized_names = ktdb["ktdb_full_name"].map(_normalize_name)
    mapping = pd.DataFrame(
        {
            "ktdb_admin_code": ktdb["ktdb_admin_code"],
            "ktdb_full_name": ktdb["ktdb_full_name"],
            "sgis_adm_cd": normalized_names.map(unique_sgis["adm_cd"]),
            "sgis_adm_nm": normalized_names.map(unique_sgis["adm_nm"]),
            "x": normalized_names.map(unique_sgis["x"]),
            "y": normalized_names.map(unique_sgis["y"]),
            "candidate_count": normalized_names.map(candidate_counts).fillna(0).astype("Int64"),
        }
    )
    mapping["match_status"] = "matched"
    mapping.loc[mapping["candidate_count"].eq(0), "match_status"] = "name_not_found"
    mapping.loc[mapping["candidate_count"].gt(1), "match_status"] = "ambiguous_name"
    mapping = mapping.drop_duplicates("ktdb_admin_code", keep="first")
    return mapping[list(MAPPING_COLUMNS)].reset_index(drop=True)


def attach_admin_centroids(frame: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    """KTDB 코드에 매핑된 SGIS 원 좌표를 출발·도착 컬럼으로 붙인다."""

    required = {"origin_admin_dong", "destination_admin_dong"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"행정동 join에 필요한 컬럼이 없습니다: {missing}")
    if mapping["ktdb_admin_code"].duplicated().any():
        raise ValueError("KTDB 행정동 mapping code는 유일해야 합니다")
    lookup = mapping.set_index("ktdb_admin_code")
    result = frame.copy()
    result["origin_x"] = pd.to_numeric(result["origin_admin_dong"].map(lookup["x"]), errors="coerce")
    result["origin_y"] = pd.to_numeric(result["origin_admin_dong"].map(lookup["y"]), errors="coerce")
    result["destination_x"] = pd.to_numeric(
        result["destination_admin_dong"].map(lookup["x"]), errors="coerce"
    )
    result["destination_y"] = pd.to_numeric(
        result["destination_admin_dong"].map(lookup["y"]), errors="coerce"
    )
    return result


def build_unmatched_report(frame: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    """좌표가 붙지 않은 비어 있지 않은 행정동 코드를 위치별로 집계한다."""

    lookup = mapping.set_index("ktdb_admin_code")
    rows: list[dict[str, object]] = []
    for side in ("origin", "destination"):
        code_column = f"{side}_admin_dong"
        x_column = f"{side}_x"
        unmatched = frame.loc[frame[code_column].astype("string").fillna("").ne("") & frame[x_column].isna()]
        for code, count in unmatched[code_column].astype(str).value_counts().items():
            detail = lookup.loc[code] if code in lookup.index else None
            rows.append(
                {
                    "side": side,
                    "ktdb_admin_code": code,
                    "ktdb_full_name": detail["ktdb_full_name"] if detail is not None else "",
                    "match_status": detail["match_status"] if detail is not None else "code_not_in_lookup",
                    "row_count": int(count),
                }
            )
    return pd.DataFrame(
        rows,
        columns=("side", "ktdb_admin_code", "ktdb_full_name", "match_status", "row_count"),
    ).sort_values(["side", "row_count", "ktdb_admin_code"], ascending=[True, False, True])
