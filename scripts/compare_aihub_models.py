"""Run the fixed AI-Hub candidate matrix on one disjoint split manifest."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.aihub.training import train_model


DEFAULT_CANDIDATES = (
    ("random_forest", "none"),
    ("random_forest", "balanced"),
    ("extra_trees", "balanced"),
    ("hist_gradient_boosting", "balanced"),
    ("catboost", "balanced"),
)


def compare(dataset_csv: str | Path, output_dir: str | Path, *, split_manifest: str | Path | None = None, n_estimators: int = 200) -> list[dict[str, object]]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for model_type, weight in DEFAULT_CANDIDATES:
        slug = f"{model_type}_{weight}"
        result = train_model(
            dataset_csv,
            output / f"{slug}.joblib",
            output / f"{slug}.json",
            model_type=model_type,
            n_estimators=n_estimators,
            class_weight=None if weight == "none" else "balanced",
            split_manifest_path=split_manifest,
        )
        for split in ("validation", "test"):
            metrics = result["metrics"][split]
            rows.append({
                "candidate": slug,
                "model_type": model_type,
                "class_weight": weight,
                "split": split,
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
                "weighted_f1": metrics["weighted_f1"],
                "brier_score": metrics["brier_score"],
            })
    with (output / "comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output / "comparison.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("output_dir")
    parser.add_argument("--split-manifest", default=None)
    parser.add_argument("--n-estimators", type=int, default=200)
    args = parser.parse_args()
    print(json.dumps(compare(args.dataset_csv, args.output_dir, split_manifest=args.split_manifest, n_estimators=args.n_estimators), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
