"""Run the existing production pipeline against frozen Seoul synthetic v3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.evaluate_dataset_v1 import run_evaluation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", default=str(ROOT / "data/evaluation/seoul-synthetic/evaluation_dataset_v3"))
    parser.add_argument("--run-dir", default=str(ROOT / "reports/evaluation_v3_baseline"))
    parser.add_argument("--canopy-baseline-commit", required=True)
    parser.add_argument("--evaluation-commit", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-hash-verification", action="store_true")
    parser.add_argument("--mobility-model", default=None, help="Optional model artifact path; default keeps the production GeoLife model")
    parser.add_argument("--window-seconds", type=int, default=120)
    args = parser.parse_args()
    summary = run_evaluation(
        args.dataset_root,
        args.run_dir,
        canopy_baseline_commit=args.canopy_baseline_commit,
        evaluation_commit=args.evaluation_commit,
        limit=args.limit,
        resume=args.resume,
        verify_hashes=not args.skip_hash_verification,
        branch="evaluation/seoul-synthetic-v3-baseline",
        geolife_model_path=args.mobility_model,
        window_seconds=args.window_seconds,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
