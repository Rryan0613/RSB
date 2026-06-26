import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from paths import MODELS_DIR

DEFAULT_MODEL_PATH = MODELS_DIR / "home_win_model.joblib"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_model_tag(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value or "unversioned").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
    return cleaned or "unversioned"


def model_path_for_version(model_version: str, target_market: str = "home_win") -> Path:
    return MODELS_DIR / f"{safe_model_tag(target_market)}_model_{safe_model_tag(model_version)}.joblib"


def feature_schema_hash(feature_cols: list) -> str:
    payload = json.dumps(list(feature_cols), separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_feature_schema(features: dict, feature_cols: list) -> None:
    missing = [column for column in feature_cols if column not in features]
    if missing:
        raise ValueError(f"Model feature schema mismatch. Missing features: {', '.join(missing)}")

    non_numeric = []
    for column in feature_cols:
        value = features[column]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            non_numeric.append(column)
    if non_numeric:
        raise ValueError(f"Model feature schema mismatch. Non-numeric features: {', '.join(non_numeric)}")


def train_model(
    training_rows,
    minimum_rows=20,
    model_version="unversioned",
    target_market="home_win",
    model_path=None,
):
    if len(training_rows) < minimum_rows:
        raise ValueError(f"Need at least {minimum_rows} completed matches. Current: {len(training_rows)}")

    df = pd.DataFrame(training_rows)
    y = df["target"]
    feature_cols = [c for c in df.columns if c not in ["match_id", "target"]]

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=3000))
    ])

    model.fit(df[feature_cols], y)

    path = Path(model_path) if model_path else model_path_for_version(model_version, target_market)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model,
        "feature_cols": feature_cols,
        "feature_schema_hash": feature_schema_hash(feature_cols),
        "model_version": model_version,
        "target_market": target_market,
        "trained_rows": len(df),
        "trained_at": utc_now(),
    }, path)

    return len(df), feature_cols


def load_model_artifact(model_path=None):
    path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    return joblib.load(path)


def predict_probability(features, model_path=None):
    saved = load_model_artifact(model_path)
    model = saved["model"]
    feature_cols = saved["feature_cols"]
    validate_feature_schema(features, feature_cols)

    df = pd.DataFrame([features])
    return float(model.predict_proba(df[feature_cols])[:, 1][0])
