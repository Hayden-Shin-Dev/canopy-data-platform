"""저장된 GeoLife baseline confusion matrix의 주요 혼동을 추출한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def analyze_confusion(metrics_json: str | Path, split: str = "test") -> dict[str, object]:
    data = json.loads(Path(metrics_json).read_text(encoding="utf-8"))
    classes = data["classes"]
    matrix = data["metrics"][split]["confusion_matrix"]
    rows: dict[str, object] = {}
    for index, actual in enumerate(classes):
        predictions = [
            {"predicted": classes[column], "count": int(count)}
            for column, count in enumerate(matrix[index])
            if column != index and count
        ]
        rows[actual] = sorted(predictions, key=lambda item: item["count"], reverse=True)
    return {"metrics_json": str(metrics_json), "split": split, "classes": classes, "off_diagonal": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics_json")
    parser.add_argument("--split", default="test")
    args = parser.parse_args()
    print(json.dumps(analyze_confusion(args.metrics_json, args.split), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
