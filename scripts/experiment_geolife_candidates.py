"""GeoLife 후보 모델과 파생 GPS feature set을 같은 사용자 split에서 비교한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from scripts.train_geolife_baseline import EXPECTED_CLASSES, METADATA_COLUMNS


def _feature_frame(frame: pd.DataFrame, feature_set: str) -> tuple[pd.DataFrame, list[str]]:
    base = [column for column in frame.columns if column not in METADATA_COLUMNS]
    features = frame[base].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if feature_set == "base":
        return features, base
    if feature_set != "derived":
        raise ValueError("feature_set은 base 또는 derived여야 합니다")

    derived = pd.DataFrame(index=frame.index)
    distance = features["distance_m"].clip(lower=1e-6)
    duration = features["observed_duration_sec"].clip(lower=1e-6)
    mean_speed = features["mean_speed_mps"].clip(lower=1e-6)
    derived["displacement_distance_ratio"] = features["displacement_m"] / distance
    derived["distance_per_second_mps"] = features["distance_m"] / duration
    derived["speed_range_mps"] = features["max_speed_mps"] - features["mean_speed_mps"]
    derived["speed_cv"] = features["speed_std_mps"] / mean_speed
    derived["acceleration_speed_ratio"] = features["mean_abs_acceleration_mps2"] / mean_speed
    derived["valid_step_ratio"] = features["valid_step_count"] / features["point_count"].clip(lower=1)
    derived["gap_step_ratio"] = features["gap_step_count"] / features["point_count"].clip(lower=1)
    derived["altitude_per_distance"] = features["altitude_range_m"] / distance
    derived = derived.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    output = pd.concat([features, derived], axis=1)
    return output, list(output.columns)


def _make_model(name: str):
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=120, random_state=2021, n_jobs=-1, class_weight=None)
    if name == "extra_trees":
        return ExtraTreesClassifier(n_estimators=120, random_state=2021, n_jobs=-1, class_weight=None)
    if name == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(max_iter=180, learning_rate=0.08, max_leaf_nodes=31, random_state=2021)
    if name == "catboost":
        try:
            from catboost import CatBoostClassifier
        except ImportError as error:
            raise RuntimeError("CatBoost가 설치되어 있지 않습니다") from error
        return CatBoostClassifier(
            iterations=250,
            depth=8,
            learning_rate=0.08,
            loss_function="MultiClass",
            random_seed=2021,
            thread_count=-1,
            verbose=False,
        )
    raise ValueError(f"지원하지 않는 model: {name}")


def _evaluate(model, x: pd.DataFrame, y: pd.Series, classes: list[str]) -> dict[str, object]:
    predicted = model.predict(x)
    predicted = np.asarray(predicted).reshape(-1)
    report = classification_report(y, predicted, labels=classes, output_dict=True, zero_division=0)
    return {
        "row_count": int(len(y)),
        "accuracy": float(accuracy_score(y, predicted)),
        "macro_f1": float(f1_score(y, predicted, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y, predicted, average="weighted", zero_division=0)),
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y, predicted, labels=classes).tolist(),
    }


def run_experiments(dataset_csv: str | Path, output_json: str | Path) -> dict[str, object]:
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    required = {"split", "canonical_mode", "user_id"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"필수 column이 없습니다: {missing}")
    classes = list(EXPECTED_CLASSES)
    results: list[dict[str, object]] = []
    for feature_set in ("base", "derived"):
        features, columns = _feature_frame(frame, feature_set)
        split_frames = {name: frame[frame["split"] == name] for name in ("train", "validation", "test")}
        split_features = {name: features.loc[data.index] for name, data in split_frames.items()}
        for model_name in ("random_forest", "extra_trees", "hist_gradient_boosting", "catboost"):
            model = _make_model(model_name)
            model.fit(split_features["train"], split_frames["train"]["canonical_mode"])
            results.append(
                {
                    "model": model_name,
                    "feature_set": feature_set,
                    "feature_columns": columns,
                    "metrics": {
                        name: _evaluate(model, split_features[name], split_frames[name]["canonical_mode"], classes)
                        for name in ("validation", "test")
                    },
                }
            )
    selected = max(results, key=lambda item: item["metrics"]["validation"]["macro_f1"])  # type: ignore[index]
    payload = {
        "dataset_csv": str(dataset_csv),
        "split_rule": "existing user-level train/validation/test split; test is never used for selection",
        "classes": classes,
        "candidate_count": len(results),
        "selected_by": "validation_macro_f1",
        "selected": {"model": selected["model"], "feature_set": selected["feature_set"]},
        "candidates": results,
    }
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("output_json")
    args = parser.parse_args()
    payload = run_experiments(args.dataset_csv, args.output_json)
    for candidate in payload["candidates"]:
        metrics = candidate["metrics"]
        print(candidate["model"], candidate["feature_set"], metrics["validation"]["macro_f1"], metrics["test"]["macro_f1"])
    print("selected", payload["selected"])


if __name__ == "__main__":
    main()
