"""Serving the classifier (given): load the MLflow "champion", or a local file as fallback."""

from __future__ import annotations

import os

LOCAL_MODEL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                           "data", "models", "annex3.joblib")


class AreaClassifier:
    def __init__(self, sk_model, version="local"):
        self.model, self.version = sk_model, version

    def predict(self, text: str) -> dict:
        probs = self.model.predict_proba([text])[0]
        i = int(probs.argmax())
        return {"label": str(self.model.classes_[i]), "probability": float(probs[i]), "version": self.version}


def load_classifier(settings):
    try:
        import mlflow
        import mlflow.sklearn
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        return AreaClassifier(mlflow.sklearn.load_model(settings.classifier_model_uri), settings.classifier_model_uri)
    except Exception:
        import joblib
        if os.path.exists(LOCAL_MODEL):
            return AreaClassifier(joblib.load(LOCAL_MODEL), "local-file")
        return None
