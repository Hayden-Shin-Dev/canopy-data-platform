"""KTDB Code Book을 기준으로 변수 설명과 코드값을 읽는다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd


class CodebookError(ValueError):
    """Code Book 형식이 예상과 다를 때 발생하는 오류."""


def normalize_code(value: object) -> str:
    """엑셀 숫자·문자 코드를 비교 가능한 문자열로 맞춘다."""

    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return str(int(number)) if number.is_integer() else text


@dataclass(frozen=True)
class Codebook:
    """Code Book에서 읽은 변수 레이블과 값 사전."""

    variable_labels: Mapping[str, str]
    values: Mapping[str, Mapping[str, str]]
    sheets: tuple[str, ...]

    def label(self, variable: str) -> str:
        """변수 레이블을 반환하고 없으면 명확한 오류를 낸다."""

        try:
            return self.variable_labels[variable]
        except KeyError as exc:
            raise CodebookError(f"Code Book에 없는 변수: {variable}") from exc

    def values_for(self, variable: str) -> Mapping[str, str]:
        """변수의 코드→레이블 사전을 반환한다."""

        return self.values.get(variable, {})


def _sheet_with_keyword(sheet_names: list[str], keyword: str) -> str:
    for name in sheet_names:
        if keyword.casefold() in name.casefold():
            return name
    raise CodebookError(f"Code Book에서 '{keyword}' 시트를 찾지 못함")


def load_codebook(path: Path) -> Codebook:
    """실제 workbook의 시트 구조를 확인한 뒤 Codebook을 만든다."""

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    workbook = pd.ExcelFile(path)
    variable_sheet = _sheet_with_keyword(workbook.sheet_names, "data")
    value_sheet = _sheet_with_keyword(workbook.sheet_names, "value")

    raw_variables = pd.read_excel(path, sheet_name=variable_sheet, header=None)
    if raw_variables.shape[1] < 2:
        raise CodebookError("변수 설명 시트에 최소 2개 열이 필요함")
    variable_labels: dict[str, str] = {}
    for _, row in raw_variables.iloc[1:, :2].iterrows():
        variable = str(row.iloc[0]).strip()
        label = str(row.iloc[1]).strip()
        if variable and variable.casefold() != "nan" and label.casefold() != "nan":
            variable_labels[variable] = label

    raw_values = pd.read_excel(path, sheet_name=value_sheet, header=None)
    if raw_values.shape[1] < 3 or len(raw_values) < 3:
        raise CodebookError("값 사전 시트의 열 또는 행이 부족함")
    values_frame = raw_values.iloc[2:, :3].copy()
    values_frame.columns = ["variable", "code", "label"]
    values_frame["variable"] = values_frame["variable"].ffill()
    values: dict[str, dict[str, str]] = {}
    for _, row in values_frame.iterrows():
        variable = str(row["variable"]).strip()
        code = normalize_code(row["code"])
        label = str(row["label"]).strip()
        if not variable or variable.casefold() == "nan" or not code:
            continue
        if label.casefold() == "nan":
            label = ""
        values.setdefault(variable, {})[code] = label

    return Codebook(variable_labels, values, tuple(workbook.sheet_names))

