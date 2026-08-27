"""Expected Behaviour 모델의 mode 확률 예측 API와 CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.config import MODELS_DIR
from src.ktdb.model_data import prepare_prediction_features
from src.ktdb.lookup import MODE_CLASSES


DEFAULT_MODEL = MODELS_DIR / "expected_behaviour" / "ktdb_population_baseline.pkl"


def _load_model(path: str | Path) -> tuple[object, str]:
    """CatBoost artifact를 먼저 시도하고, 없으면 sklearn bundle을 읽는다."""

    try:
        from catboost import CatBoostClassifier

        model = CatBoostClassifier()
        model.load_model(str(path))
        return model, "catboost"
    except (ImportError, Exception):
        import joblib

        bundle = joblib.load(path)
        if not isinstance(bundle, dict) or bundle.get("backend") != "sklearn":
            raise ValueError("지원하는 모델 artifact 형식이 아닙니다")
        return bundle["model"], "sklearn"


def predict_expected_behaviour(
    frame: pd.DataFrame,
    model_path: str | Path = DEFAULT_MODEL,
) -> pd.DataFrame:
    """입력 rows에 대해 mode별 확률과 최상위 예측을 반환한다."""

    model, _backend = _load_model(model_path)
    features, _categorical, _numeric = prepare_prediction_features(frame)
    probabilities = model.predict_proba(features)
    classes = [str(value) for value in getattr(model, "classes_", MODE_CLASSES)]
    result = pd.DataFrame(probabilities, columns=[f"{label}_probability" for label in classes])
    for mode in MODE_CLASSES:
        column = f"{mode}_probability"
        if column not in result:
            result[column] = 0.0
    result = result[[f"{mode}_probability" for mode in MODE_CLASSES]]
    result["predicted_mode"] = result[[f"{mode}_probability" for mode in MODE_CLASSES]].idxmax(axis=1).str.removesuffix("_probability")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    predictions = predict_expected_behaviour(
        pd.read_csv(args.dataset, encoding="utf-8-sig"), args.model
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(json.dumps({"rows": len(predictions), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
