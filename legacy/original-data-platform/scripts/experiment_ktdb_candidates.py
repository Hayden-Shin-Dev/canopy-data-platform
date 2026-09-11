"""KTDB CatBoost 설정을 같은 person-level split에서 비교한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.ktdb.model_data import split_model_data
from src.predict_expected_behaviour import _load_model


CLASSES = ("walk", "bike", "car", "bus", "rail")


def _brier_score(target: pd.Series, probabilities, classes: list[str]) -> float:
    class_index = {label: index for index, label in enumerate(classes)}
    total = 0.0
    for label, row in zip(target.astype(str), probabilities):
        expected = [0.0] * len(classes)
        expected[class_index[label]] = 1.0
        total += sum((float(actual) - wanted) ** 2 for actual, wanted in zip(row, expected))
    return total / len(target)


def _evaluate(model: object, data, *, split: str) -> dict[str, object]:
    from sklearn.metrics import accuracy_score, f1_score, log_loss

    probabilities = model.predict_proba(data.features)
    model_classes = [str(value) for value in getattr(model, "classes_", CLASSES)]
    ordered = []
    for label in CLASSES:
        index = model_classes.index(label)
        ordered.append([float(row[index]) for row in probabilities])
    ordered_matrix = list(map(list, zip(*ordered)))
    predicted = [CLASSES[max(range(len(CLASSES)), key=lambda i: row[i])] for row in ordered_matrix]
    log_loss_labels = sorted(CLASSES)
    log_loss_matrix = [[row[CLASSES.index(label)] for label in log_loss_labels] for row in ordered_matrix]
    return {
        "split": split,
        "row_count": int(len(data.target)),
        "accuracy": float(accuracy_score(data.target, predicted)),
        "macro_f1": float(f1_score(data.target, predicted, labels=list(CLASSES), average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(data.target, predicted, labels=list(CLASSES), average="weighted", zero_division=0)),
        "log_loss": float(log_loss(data.target, log_loss_matrix, labels=log_loss_labels)),
        "multiclass_brier": float(_brier_score(data.target, ordered_matrix, list(CLASSES))),
    }


def _fit_catboost(train, validation, *, iterations: int, depth: int, learning_rate: float, seed: int):
    from catboost import CatBoostClassifier

    model = CatBoostClassifier(
        iterations=iterations,
        depth=depth,
        learning_rate=learning_rate,
        random_seed=seed,
        loss_function="MultiClass",
        verbose=False,
    )
    model.fit(
        train.features,
        train.target,
        cat_features=list(train.categorical_features),
        eval_set=(validation.features, validation.target),
        use_best_model=True,
    )
    return model


def experiment(dataset_csv: str | Path, baseline_model: str | Path, output_json: str | Path, selected_model_path: str | Path | None = None) -> dict[str, object]:
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig")
    splits = split_model_data(frame)
    train, validation, test = splits["train"], splits["validation"], splits["test"]
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline, backend = _load_model(baseline_model)
    candidates: list[dict[str, object]] = []
    candidate_models: dict[str, object] = {"existing_catboost": baseline}
    candidates.append({
        "name": "existing_catboost",
        "config": {"source": str(baseline_model)},
        "metrics": {split: _evaluate(baseline, data, split=split) for split, data in (("validation", validation), ("test", test))},
    })
    if backend == "catboost":
        candidate_specs = (("catboost_depth6", {"iterations": 250, "depth": 6, "learning_rate": 0.08}), ("catboost_depth10", {"iterations": 250, "depth": 10, "learning_rate": 0.05}))
        for name, config in candidate_specs:
            model = _fit_catboost(train, validation, seed=2021, **config)
            candidate_models[name] = model
            candidates.append({"name": name, "config": config, "metrics": {split: _evaluate(model, data, split=split) for split, data in (("validation", validation), ("test", test))}})
    else:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OrdinalEncoder

        for name, config in (("histgradientboosting_leaf31", {"max_iter": 120, "max_leaf_nodes": 31}), ("histgradientboosting_leaf63", {"max_iter": 120, "max_leaf_nodes": 63})):
            preprocessor = ColumnTransformer([("categorical", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), list(train.categorical_features)), ("numeric", SimpleImputer(strategy="constant", fill_value=0.0, keep_empty_features=True), list(train.numeric_features))])
            model = Pipeline([("preprocessor", preprocessor), ("classifier", HistGradientBoostingClassifier(learning_rate=0.08, random_state=2021, **config))])
            model.fit(train.features, train.target)
            candidate_models[name] = model
            candidates.append({"name": name, "config": config, "metrics": {split: _evaluate(model, data, split=split) for split, data in (("validation", validation), ("test", test))}})
    selected = max(candidates, key=lambda item: float(item["metrics"]["validation"]["macro_f1"]))
    if selected_model_path is not None:
        import joblib

        selected_path = Path(selected_model_path)
        selected_path.parent.mkdir(parents=True, exist_ok=True)
        selected_model = candidate_models[selected["name"]]
        if backend == "catboost":
            selected_model.save_model(str(selected_path))
        else:
            joblib.dump({"backend": "sklearn", "model": selected_model}, selected_path)
    result = {
        "dataset_csv": str(dataset_csv),
        "baseline_backend": backend,
        "split_rule": "existing person-level train/validation/test split; validation selects the candidate",
        "classes": list(CLASSES),
        "selected_by": "validation.macro_f1",
        "selected": selected["name"],
        "selected_model_path": str(selected_model_path) if selected_model_path is not None else None,
        "candidates": candidates,
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv", type=Path)
    parser.add_argument("baseline_model", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--selected-model", type=Path)
    args = parser.parse_args()
    print(json.dumps(experiment(args.dataset_csv, args.baseline_model, args.output_json, args.selected_model), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
