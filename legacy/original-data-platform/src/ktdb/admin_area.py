"""행정동 코드 workbook을 조회 가능한 표로 정리한다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .codebook import normalize_code


ADMIN_COLUMN_MAP = {
    "행정동코드": "admin_code",
    "시도명": "sido",
    "시군구명": "sigungu",
    "읍면동명": "admin_name",
    "생성일자": "created_date",
    "말소일자": "abolished_date",
}


def _clean_text(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def load_admin_lookup(path: Path) -> pd.DataFrame:
    """행정동 코드별 대표 레코드를 반환한다.

    같은 행정동 코드가 여러 법정동에 반복될 수 있으므로, 말소되지 않은
    레코드를 우선하고 생성일자가 가장 최근인 행을 대표값으로 선택한다.
    """

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = pd.read_excel(path, dtype={"행정동코드": "string"})
    missing = set(ADMIN_COLUMN_MAP) - set(raw.columns)
    if missing:
        raise ValueError(f"행정동 workbook에 없는 컬럼: {sorted(missing)}")

    frame = raw.rename(columns=ADMIN_COLUMN_MAP)[list(ADMIN_COLUMN_MAP.values())].copy()
    frame["admin_code"] = frame["admin_code"].map(normalize_code)
    for column in ("sido", "sigungu", "admin_name"):
        frame[column] = _clean_text(frame[column])
    frame["created_date"] = pd.to_datetime(
        _clean_text(frame["created_date"]),
        format="%Y%m%d",
        errors="coerce",
    )
    frame["abolished_date"] = frame["abolished_date"].map(normalize_code)
    frame = frame[frame["admin_code"].ne("")].copy()

    # 활성 레코드를 먼저 정렬한 뒤 중복 코드당 첫 행만 남긴다.
    frame["_active"] = frame["abolished_date"].eq("")
    frame = frame.sort_values(
        ["admin_code", "_active", "created_date"],
        ascending=[True, False, False],
        kind="mergesort",
    )
    frame = frame.drop_duplicates("admin_code", keep="first")
    return frame.drop(columns="_active").set_index("admin_code", drop=False)
