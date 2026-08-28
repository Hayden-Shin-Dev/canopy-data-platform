"""Validation Macro F1 기준으로 GeoLife 후보 모델을 선택한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def select_model(metrics_paths: list[str | Path]) -> dict[str, object]:
    """후보 metrics JSON을 읽고 Test 지표를 보지 않고 하나를 선택한다."""

    if not metrics_paths:
        raise ValueError("최소 하나의 metrics JSON이 필요합니다")

    candidates: list[dict[str, object]] = []
    for raw_path in metrics_paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        validation = payload.get("metrics", {}).get("validation", {})
        macro_f1 = validation.get("macro_f1")
        if not isinstance(macro_f1, (int, float)):
            raise ValueError(f"Validation Macro F1이 없습니다: {path}")
        candidates.append(
            {
                "metrics_path": str(path),
                "model": payload.get("model"),
                "class_weight": payload.get("class_weight"),
                "validation_accuracy": validation.get("accuracy"),
                "validation_macro_f1": float(macro_f1),
                "validation_weighted_f1": validation.get("weighted_f1"),
            }
        )

    # 동점이면 입력 순서를 유지해 결과가 재현되도록 한다.
    selected = max(candidates, key=lambda candidate: candidate["validation_macro_f1"])
    return {
        "selection_metric": "validation_macro_f1",
        "selected": selected,
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics_paths", nargs="+", help="후보 metrics JSON 경로")
    parser.add_argument("--output", required=True, help="선택 결과 JSON 경로")
    args = parser.parse_args()

    result = select_model(args.metrics_paths)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
