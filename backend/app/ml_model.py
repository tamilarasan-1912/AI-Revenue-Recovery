"""Dataset-trained ML model for payment-recovery propensity.

The uploaded CSV is the training source.  The model estimates the probability
that a failed payment is recoverable.  Research-backed recovery logic then
uses that probability together with the failure/issuer context to choose the
next safe recovery action.

Important: this model does not invent payment outcomes. ``is_recoverable`` is
used only as the training target; it is never an input feature.
"""
from __future__ import annotations

from typing import Any

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


OPTIONAL_FEATURES = (
    "payment_method",
    "decline_code",
    "error_source",
    "error_step",
    "currency",
    "is_recurring",
    "authentication_required",
    "card_expiry_days",
    "customer_tenure_days",
    "previous_payment_success_rate",
    "days_past_due",
    "hour_of_day",
    "day_of_week",
)


class RecoveryMLModel:
    def __init__(self) -> None:
        self.model: Pipeline | None = None
        self.training_rows = 0
        self.classes: list[str] = []
        self.version = "recoverability-rf-v2-research-backed"
        self.training_metrics: dict[str, Any] = {}
        self.feature_names: list[str] = []

    @staticmethod
    def _features(row: dict[str, Any]) -> dict[str, Any]:
        """Create model features without using the target label."""
        features: dict[str, Any] = {
            "failure_reason": str(row.get("failure_reason", "unknown")).strip().lower(),
            "amount": float(row.get("amount", 0) or 0),
            "retry_count": int(row.get("retry_count", 0) or 0),
        }

        # Optional provider/customer context.  Older CSVs can omit these
        # columns; newer Razorpay-style exports can supply them.
        for name in OPTIONAL_FEATURES:
            value = row.get(name)
            if value is None or value == "":
                continue
            if name in {"is_recurring", "authentication_required"}:
                features[name] = str(value).strip().lower() in {"true", "1", "yes", "y"}
            elif name in {
                "card_expiry_days",
                "customer_tenure_days",
                "previous_payment_success_rate",
                "days_past_due",
                "hour_of_day",
                "day_of_week",
            }:
                try:
                    features[name] = float(value)
                except (TypeError, ValueError):
                    continue
            else:
                features[name] = str(value).strip().lower()

        # Stable, research-relevant engineered signals.
        features["amount_log"] = __import__("math").log1p(max(0.0, features["amount"]))
        features["retry_pressure"] = min(1.0, features["retry_count"] / 3.0)
        return features

    def fit(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        clean = [r for r in rows if isinstance(r, dict)]
        if not clean:
            self.model = None
            self.training_rows = 0
            self.classes = []
            self.training_metrics = {}
            self.feature_names = []
            return self.status()

        x = [self._features(r) for r in clean]
        y = ["recoverable" if bool(r.get("is_recoverable")) else "not_recoverable" for r in clean]
        unique = sorted(set(y))

        estimator = DummyClassifier(strategy="prior", random_state=42) if len(unique) < 2 else RandomForestClassifier(
            n_estimators=250,
            max_depth=12,
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
        self.feature_names = list(self.model.named_steps["features"].get_feature_names_out())

        self.training_metrics = self._holdout_metrics(clean, y, unique)
        return self.status()

    def _holdout_metrics(
        self,
        rows: list[dict[str, Any]],
        labels: list[str],
        unique: list[str],
    ) -> dict[str, Any]:
        """Report a holdout score when the uploaded dataset is large enough.

        For very small or one-class datasets we intentionally report that a
        meaningful holdout metric is unavailable instead of fabricating one.
        """
        if len(rows) < 30 or len(unique) < 2:
            return {"holdout_available": False, "reason": "Need >=30 rows and both classes"}
        try:
            train_rows, test_rows, train_y, test_y = train_test_split(
                rows,
                labels,
                test_size=0.20,
                random_state=42,
                stratify=labels,
            )
            estimator = RandomForestClassifier(
                n_estimators=200,
                max_depth=12,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
            validation_model = Pipeline([
                ("features", DictVectorizer(sparse=True)),
                ("model", estimator),
            ])
            validation_model.fit([self._features(r) for r in train_rows], train_y)
            predictions = validation_model.predict([self._features(r) for r in test_rows])
            probabilities = validation_model.predict_proba([self._features(r) for r in test_rows])
            classes = list(validation_model.named_steps["model"].classes_)
            positive_index = classes.index("recoverable")
            return {
                "holdout_available": True,
                "test_rows": len(test_rows),
                "accuracy": round(float(accuracy_score(test_y, predictions)), 4),
                "roc_auc": round(float(roc_auc_score(
                    [1 if y == "recoverable" else 0 for y in test_y],
                    probabilities[:, positive_index],
                )), 4),
            }
        except Exception as exc:
            return {"holdout_available": False, "reason": f"validation_unavailable:{exc.__class__.__name__}"}

    def predict_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Run batch inference in one sklearn call."""
        if self.model is None:
            raise RuntimeError("No uploaded dataset has trained the ML model yet.")
        if not rows:
            return []

        x = [self._features(row) for row in rows]
        probabilities = self.model.predict_proba(x)
        classes = [str(label) for label in self.model.named_steps["model"].classes_]
        results: list[dict[str, Any]] = []

        for probability_row in probabilities:
            probability_map = {label: float(prob) for label, prob in zip(classes, probability_row)}
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
            "feature_count": len(self.feature_names),
            "training_metrics": self.training_metrics,
        }


ml_model = RecoveryMLModel()
