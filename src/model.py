import pandas as pd
import joblib
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

MODEL_PATH = Path("models/home_win_model.joblib")

def train_model(training_rows, minimum_rows=20):
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

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_cols": feature_cols}, MODEL_PATH)

    return len(df), feature_cols

def predict_probability(features):
    saved = joblib.load(MODEL_PATH)
    model = saved["model"]
    feature_cols = saved["feature_cols"]

    df = pd.DataFrame([features])
    return float(model.predict_proba(df[feature_cols])[:, 1][0])
