"""Canopy 파이프라인에서 함께 쓰는 저장소 경로와 기본 상수 모음."""

from __future__ import annotations

from pathlib import Path


# 이 파일은 실행 위치가 어디든 저장소 루트를 같은 곳으로 잡기 위한 기준점임.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 원본은 읽기 전용으로 두고, 중간·최종 결과는 별도 폴더에 생성하는 구조임.
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
KTDB_RAW_DIR = RAW_DIR / "ktdb"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"
REPORTS_DIR = PROJECT_ROOT / "reports"
MODELS_DIR = PROJECT_ROOT / "models"

SGIS_CENTROID_PATH = REFERENCE_DIR / "admin_dong_centroids_2021.csv"
SGIS_RAW_RESPONSE_DIR = REFERENCE_DIR / "sgis" / "raw" / "2021"
KTDB_SGIS_MAPPING_PATH = REFERENCE_DIR / "ktdb_sgis_admin_dong_mapping_2021.csv"
KTDB_UNMATCHED_REPORT_PATH = REPORTS_DIR / "ktdb_admin_dong_unmatched.csv"

# KTDB 파일명은 원본에서 받은 이름을 그대로 사용해야 하므로 여기서 한 번만 관리함.
KTDB_RAW_FILES = {
    "person": "①개인특성.csv",
    "trip": "②이동특성.csv",
    "codebook": "Code book.xlsx",
    "admin_area": "행정동코드_20210726(말소코드포함).xlsx",
}

# 출발 분은 15분 단위로 묶고, 자정 전후 시간도 같은 규칙으로 처리한다.
MINUTE_BIN_SIZE = 15
TIME_BANDS: tuple[tuple[str, int, int], ...] = (
    ("late_night", 0, 4),
    ("early_morning", 4, 7),
    ("morning_peak", 7, 10),
    ("daytime", 10, 17),
    ("evening_peak", 17, 20),
    ("night", 20, 24),
)

# 같은 사람의 통행이 서로 다른 split에 섞이지 않도록 그룹 기준을 고정한다.
RANDOM_SEED = 2021
SPLIT_RATIOS = {"train": 0.70, "validation": 0.15, "test": 0.15}

# 실제 도로거리가 아니라 행정동 중심점 직선거리 기준의 구간 경계임.
DISTANCE_BANDS: tuple[tuple[str, float, float | None], ...] = (
    ("0-2km", 0.0, 2.0),
    ("2-5km", 2.0, 5.0),
    ("5-10km", 5.0, 10.0),
    ("10-20km", 10.0, 20.0),
    ("20km+", 20.0, None),
)
