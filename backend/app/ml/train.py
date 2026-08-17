"""
SecureRotate AI - ML Model Training Pipeline
Trains a RandomForestClassifier for credential risk level prediction and saves the serialized model.
"""

import sys
import os

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.ml.features import build_preprocessor


def train_and_evaluate_model():
    """Loads synthetic dataset, trains RandomForest model, prints metrics, and saves model binary."""
    dataset_path = os.path.join(os.path.dirname(__file__), "dataset.csv")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found at {dataset_path}")

    df = pd.read_csv(dataset_path)

    X = df.drop(columns=["risk_level"])
    y = df["risk_level"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=100, max_depth=10, random_state=42
                ),
            ),
        ]
    )

    print("Training RandomForestClassifier model...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted")
    rec = recall_score(y_test, y_pred, average="weighted")
    f1 = f1_score(y_test, y_pred, average="weighted")

    print("\n================ MODEL EVALUATION METRICS ================")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print("==========================================================")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Save trained pipeline model
    models_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(models_dir, exist_ok=True)
    model_filepath = os.path.join(models_dir, "risk_model.pkl")

    joblib.dump(pipeline, model_filepath)
    print(f"Model saved successfully to: {model_filepath}")

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "model_path": model_filepath,
    }


if __name__ == "__main__":
    train_and_evaluate_model()
