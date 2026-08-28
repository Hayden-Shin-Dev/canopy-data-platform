"""GeoLife raw label부터 selected Window까지 mode별 보존 여부를 비교한다."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from src.geolife.mode_mapping import EXCLUDED_RAW_MODES, RAW_TO_CANOPY, canonicalize_mode
from src.geolife.raw import iter_label_intervals


def analyze_label_pipeline(
    zip_path: str | Path,
    window_csv: str | Path,
    window_summary_json: str | Path,
) -> dict[str, object]:
    raw_rows: Counter[str] = Counter(interval.mode_raw for interval in iter_label_intervals(zip_path))
    frame = pd.read_csv(window_csv, encoding="utf-8-sig", dtype={"canonical_mode": "string"})
    summary = json.loads(Path(window_summary_json).read_text(encoding="utf-8"))
    unknown = sorted(set(raw_rows) - set(RAW_TO_CANOPY) - set(EXCLUDED_RAW_MODES))
    return {
        "raw_label_row_counts": dict(sorted(raw_rows.items())),
        "raw_modes_with_mapping": {
            raw: canonicalize_mode(raw) for raw in sorted(raw_rows) if raw in RAW_TO_CANOPY
        },
        "raw_modes_excluded": {
            raw: raw_rows[raw] for raw in sorted(raw_rows) if raw in EXCLUDED_RAW_MODES
        },
        "unknown_raw_modes": unknown,
        "selected_window_counts": frame["canonical_mode"].value_counts().sort_index().to_dict(),
        "window_status_counts": summary["window_status_counts"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path")
    parser.add_argument("window_csv")
    parser.add_argument("window_summary_json")
    args = parser.parse_args()
    print(json.dumps(analyze_label_pipeline(args.zip_path, args.window_csv, args.window_summary_json), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
