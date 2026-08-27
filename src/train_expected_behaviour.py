"""KTDB Population Feature로 Expected Behaviour 분류 모델을 학습한다."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import MODELS_DIR, PROCESSED_DIR
from src.ktdb.model_data import prepare_model_data, split_model_data


DEFAULT_DATASET = PROCESSED_DIR / "population_baseline" / "ktdb" / "01_population_model_training_all.csv"
DEFAULT_MODEL = MODELS_DIR / "expected_behaviour" / "ktdb_population_baseline.pkl"


@dataclass(frozen=True)
class TrainingConfig:
    iterations: int = 300
    depth: int = 8
    learning_rate: float = 0.08
    random_seed: int = 2021


def _evaluate(model: object, features: pd.DataFrame, target: pd.Series) -> dict[str, float]:
    from sklearn.metrics import accuracy_score, f1_score

    predicted = model.predict(features)
    return {
        "accuracy": float(accuracy_score(target, predicted)),
        "macro_f1": float(f1_score(target, predicted, average="macro", zero_division=0)),
    }


def train_expected_behaviour(
    frame: pd.DataFrame,
    model_path: str | Path = DEFAULT_MODEL,
    *,
    config: TrainingConfig = TrainingConfig(),
) -> dict[str, object]:
    """train split으로 학습하고 validation/test 성능과 artifact를 저장한다."""

    if config.iterations < 1 or config.depth < 1 or config.learning_rate <= 0:
        raise ValueError("iterations, depth, learning_rate는 양수여야 합니다")
    splits = split_model_data(frame)
    if "train" not in splits:
        raise ValueError("train split이 없어 모델을 학습할 수 없습니다")
    train = splits["train"]
    validation = splits.get("validation")
    test = splits.get("test")
    output = Path(model_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        from catboost import CatBoostClassifier

        model = CatBoostClassifier(
            iterations=config.iterations,
            depth=config.depth,
            learning_rate=config.learning_rate,
            random_seed=config.random_seed,
            loss_function="MultiClass",
            verbose=False,
        )
        model.fit(
            train.features,
            train.target,
            cat_features=list(train.categorical_features),
            eval_set=(validation.features, validation.target) if validation else None,
            use_best_model=validation is not None,
        )
        model.save_model(str(output))
        backend = "catboost"
    except ImportError:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OrdinalEncoder
        from sklearn.impute import SimpleImputer
        import joblib

        preprocessor = ColumnTransformer(
            [
                (
                    "categorical",
                    OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                    list(train.categorical_features),
                ),
                (
                    "numeric",
                    SimpleImputer(strategy="constant", fill_value=0.0, keep_empty_features=True),
                    list(train.numeric_features),
                ),
            ]
        )
        model = Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "classifier",
                    HistGradientBoostingClassifier(
                        max_iter=config.iterations,
                        max_leaf_nodes=2**config.depth,
                        learning_rate=config.learning_rate,
                        random_state=config.random_seed,
                    ),
                ),
            ]
        )
        model.fit(train.features, train.target)
        joblib.dump({"backend": "sklearn", "model": model}, output)
        backend = "sklearn"

    metrics: dict[str, object] = {"train": _evaluate(model, train.features, train.target)}
    if validation:
        metrics["validation"] = _evaluate(model, validation.features, validation.target)
    if test:
        metrics["test"] = _evaluate(model, test.features, test.target)
    return {"backend": backend, "model_path": str(output), "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--iterations", type=int, default=300)
    args = parser.parse_args()
    frame = pd.read_csv(args.dataset, encoding="utf-8-sig")
    result = train_expected_behaviour(
        frame,
        args.model,
        config=TrainingConfig(iterations=args.iterations),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
