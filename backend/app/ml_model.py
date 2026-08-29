"""Dataset-trained ML model used by RecoverAI.

The uploaded CSV is the only training source. The model predicts recoverability
from transaction amount, failure reason and retry count. The label is never
supplied to the model as an input feature.
"""
from typing import Any

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline


class RecoveryMLModel:
    def __init__(self) -> None:
        self.model: Pipeline | None = None
        self.training_rows = 0
        self.classes: list[str] = []
        self.version = "recoverability-rf-v1"

    @staticmethod
    def _features(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "failure_reason": str(row.get("failure_reason", "unknown")).strip().lower(),
            "amount": float(row.get("amount", 0) or 0),
            "retry_count": int(row.get("retry_count", 0) or 0),
        }

    def fit(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        clean = [r for r in rows if isinstance(r, dict)]
        if not clean:
            self.model = None
            self.training_rows = 0
            self.classes = []
            return self.status()

        x = [self._features(r) for r in clean]
        y = ["recoverable" if bool(r.get("is_recoverable")) else "not_recoverable" for r in clean]
        unique = sorted(set(y))

        estimator = DummyClassifier(strategy="prior", random_state=42) if len(unique) < 2 else RandomForestClassifier(
            n_estimators=150,
            max_depth=10,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        self.model = Pipeline([
            ("features", DictVectorizer(sparse=True)),
            ("model", estimator),
        ])
        self.model.fit(x, y)
        self.training_rows = len(clean)
        self.classes = list(getattr(estimator, "classes_", unique))
        return self.status()

    def predict_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Predict a batch in one sklearn call.

        Calling RandomForest.predict_proba once per CSV row is unnecessarily
        expensive on hosted/serverless deployments. Batch inference keeps the
        same model and output semantics while avoiding request timeouts.
        """
        if self.model is None:
            raise RuntimeError("No uploaded dataset has trained the ML model yet.")
        if not rows:
            return []

        x = [self._features(row) for row in rows]
        probabilities = self.model.predict_proba(x)
        classes = [str(label) for label in self.model.named_steps["model"].classes_]
        results: list[dict[str, Any]] = []

        for probability_row in probabilities:
            probability_map = {
                label: float(prob) for label, prob in zip(classes, probability_row)
            }
            recoverable_probability = probability_map.get("recoverable", 0.0)
            predicted = "recoverable" if recoverable_probability >= 0.5 else "not_recoverable"
            confidence = max(probability_map.values()) if probability_map else 0.5
            results.append({
                "predicted_label": predicted,
                "recoverability_probability": round(recoverable_probability, 4),
                "confidence": round(float(confidence), 4),
                "model_version": self.version,
                "training_rows": self.training_rows,
            })
        return results

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        return self.predict_many([row])[0]

    def status(self) -> dict[str, Any]:
        return {
            "trained": self.model is not None,
            "algorithm": "RandomForestClassifier" if self.model and self.model.named_steps["model"].__class__.__name__ == "RandomForestClassifier" else ("DummyClassifier" if self.model else None),
            "training_rows": self.training_rows,
            "classes": self.classes,
            "model_version": self.version,
        }


ml_model = RecoveryMLModel()
