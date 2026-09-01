"""Select deterministic AI-Hub Test UID trajectories for real-GPS replay."""

from __future__ import annotations

import argparse
import json

from src.aihub.replay import select_test_trajectories


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", help="AI-Hub dataset root containing Training/Validation")
    parser.add_argument("--windows", default="data/interim/aihub/aihub_split_windows.csv")
    parser.add_argument("--split-manifest", default="data/interim/aihub/aihub_split_manifest.json")
    parser.add_argument("--output", default="data/replay/aihub_test/AIHUB_REPLAY_MANIFEST.json")
    parser.add_argument("--per-class", type=int, default=5)
    args = parser.parse_args()
    result = select_test_trajectories(
        args.windows,
        args.split_manifest,
        args.source_root,
        args.output,
        per_class=args.per_class,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
