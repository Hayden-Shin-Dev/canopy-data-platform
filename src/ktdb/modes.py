"""KTDB 이동수단 코드에서 sequence와 대표수단을 만든다."""

from __future__ import annotations

import re
from typing import Mapping

import pandas as pd

from .codebook import Codebook, normalize_code


CANOPY_CLASSES = ("walk", "bike", "car", "bus", "rail")
MODE_PRIORITY = {"walk": 1, "bike": 2, "car": 3, "bus": 4, "rail": 5}


def _normalise_label(label: str) -> str:
    return re.sub(r"\s+", "", label).lower()


def classify_mode_label(label: str) -> tuple[str | None, str]:
    """Code Book의 한글 수단명에 근거해 class와 규칙 설명을 반환한다."""

    compact = _normalise_label(label)
    if "도보" in compact or "걸어서" in compact:
        return "walk", "도보 계열"
    if "자전거" in compact:
        return "bike", "자전거 계열"
    if "버스" in compact:
        return "bus", "버스 계열"
    if any(token in compact for token in ("지하철", "전철", "경전철", "철도", "고속철도")):
        return "rail", "철도 계열"
    if any(token in compact for token in ("승용차", "승합차", "택시", "화물차")):
        return "car", "자동차 계열"
    return None, "Canopy POC 제외 수단"


def build_mode_mapping(codebook: Codebook) -> pd.DataFrame:
    """TP5_1 Code Book 값 전체를 사람이 검토할 수 있는 표로 만든다."""

    rows = []
    for raw_code, raw_name in codebook.values_for("TP5_1").items():
        canopy_class, rule = classify_mode_label(raw_name)
        rows.append(
            {
                "raw_code": raw_code,
                "raw_name": raw_name,
                "canopy_class": canopy_class or "excluded",
                "mapping_rule": rule,
            }
        )
    return pd.DataFrame(rows).sort_values("raw_code").reset_index(drop=True)


def mode_code_map(codebook: Codebook) -> Mapping[str, str | None]:
    """Code Book 코드 문자열을 Canopy class로 연결한다."""

    return {
        raw_code: classify_mode_label(raw_name)[0]
        for raw_code, raw_name in codebook.values_for("TP5_1").items()
    }


def _segment_columns(frame: pd.DataFrame, mode_count: int = 10) -> list[tuple[str, str]]:
    columns = []
    for number in range(1, mode_count + 1):
        mode_column = f"TP5_{number}"
        duration_column = f"TP5_{number}_t1"
        if mode_column in frame.columns and duration_column in frame.columns:
            columns.append((mode_column, duration_column))
    return columns


def _parse_row(
    row: pd.Series,
    code_map: Mapping[str, str | None],
    columns: list[tuple[str, str]],
) -> tuple[str, str, str]:
    segments: list[tuple[str, str | None, float | None]] = []
    for mode_column, duration_column in columns:
        raw_code = normalize_code(row[mode_column])
        if not raw_code:
            continue
        canopy_class = code_map.get(raw_code)
        duration = pd.to_numeric(row[duration_column], errors="coerce")
        duration_value = float(duration) if pd.notna(duration) else None
        segments.append((raw_code, canopy_class, duration_value))

    if not segments:
        return "", "", ""

    sequence = "|".join(segment[1] or "excluded" for segment in segments)
    has_duration = any(segment[2] is not None for segment in segments)
    if has_duration:
        max_duration = max(
            segment[2] if segment[2] is not None else float("-inf")
            for segment in segments
        )
        candidates = [segment for segment in segments if segment[2] == max_duration]
    else:
        candidates = segments

    chosen = max(
        candidates,
        key=lambda segment: MODE_PRIORITY.get(segment[1] or "", 0),
    )
    return sequence, chosen[1] or "", chosen[0]


def derive_mode_features(frame: pd.DataFrame, codebook: Codebook) -> pd.DataFrame:
    """최대 10개 TP5 구간의 sequence와 대표수단을 추가한다."""

    columns = _segment_columns(frame)
    if not columns:
        raise ValueError("TP5 수단·소요시간 컬럼을 찾지 못함")
    code_map = mode_code_map(codebook)
    parsed = frame.apply(
        lambda row: _parse_row(row, code_map, columns),
        axis=1,
        result_type="expand",
    )
    parsed.columns = ["actual_mode_sequence", "actual_mode", "main_mode_raw_code"]
    return pd.concat([frame.copy(), parsed], axis=1)

