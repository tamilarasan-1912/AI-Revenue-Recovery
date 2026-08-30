"""Payment-recovery ML models.

The supervised target is ``is_recoverable``. It is never used as an input
feature. The model predicts recovery propensity from payment behaviour and
failure context; the deterministic recovery policy remains the final action
and safety boundary.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

OPTIONAL_FEATURES = (
    "payment_method", "decline_code", "error_source", "error_step", "currency",
    "is_recurring", "authentication_required", "card_expiry_days",
    "customer_tenure_days", "previous_payment_success_rate", "days_past_due",
    "hour_of_day", "day_of_week", "previous_payment_count",
    "previous_failed_payment_count", "previous_delayed_payment_count",
    "average_payment_delay_days", "outstanding_amount", "reminder_count",
    "reminder_response_rate",
)
NUMERIC_FEATURES = {
    "card_expiry_days", "customer_tenure_days", "previous_payment_success_rate",
    "days_past_due", "hour_of_day", "day_of_week", "previous_payment_count",
    "previous_failed_payment_count", "previous_delayed_payment_count",
    "average_payment_delay_days", "outstanding_amount", "reminder_count",
    "reminder_response_rate",
}
BOOLEAN_FEATURES = {"is_recurring", "authentication_required"}


class RecoveryMLModel:
    """Train recovery propensity and expected recovery amount models."""

    def __init__(self) -> None:
        self.classifier: Pipeline | None = None
        self.regressor: Pipeline | None = None
        self.training_rows = 0
        self.training_key: str | None = None
        self.classes: list[str] = []
        self.version = "recoverability-rf-v4-heldout-metrics"
        self.training_metrics: dict[str, Any] = {}
        self.feature_names: list[str] = []

    @staticmethod
    def _training_identity(rows: list[dict[str, Any]]) -> str:
        compact = []
        for row in rows:
            compact.append({
                key: row.get(key)
                for key in sorted(row)
                if key != 'features' or isinstance(row.get(key), dict)
            })
        payload = json.dumps(compact, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]

    @staticmethod
    def _finite_float(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return number if math.isfinite(number) else default

    @classmethod
    def _features(cls, row: dict[str, Any]) -> dict[str, Any]:
        amount = max(0.0, cls._finite_float(row.get("amount", 0)))
        retry_count = max(0, int(cls._finite_float(row.get("retry_count", 0))))
        features: dict[str, Any] = {
            "failure_reason": str(row.get("failure_reason", "unknown")).strip().lower(),
            "amount": amount,
            "retry_count": retry_count,
            "amount_log": math.log1p(amount),
            "retry_pressure": min(1.0, retry_count / 3.0),
        }
        for name in OPTIONAL_FEATURES:
            value = row.get(name)
            if value is None or value == "":
                continue
            if name in BOOLEAN_FEATURES:
                features[name] = str(value).strip().lower() in {"true", "1", "yes", "y"}
            elif name in NUMERIC_FEATURES:
                number = cls._finite_float(value, float("nan"))
                if math.isfinite(number):
                    features[name] = number
            else:
                features[name] = str(value).strip().lower()
        outstanding = max(0.0, cls._finite_float(row.get("outstanding_amount", amount), amount))
        success_rate = max(0.0, min(1.0, cls._finite_float(row.get("previous_payment_success_rate", 1.0), 1.0)))
        features["outstanding_to_amount"] = outstanding / max(amount, 1.0)
        features["payment_history_risk"] = max(0.0, min(1.0, 1.0 - success_rate))
        return features

    def fit(self, rows: list[dict[str, Any]], training_key: str | None = None) -> dict[str, Any]:
        clean = [r for r in rows if isinstance(r, dict)]
        if not clean:
            self.__init__()
            return self.status()

        x = [self._features(r) for r in clean]
        y = ["recoverable" if bool(r.get("is_recoverable")) else "not_recoverable" for r in clean]
        unique = sorted(set(y))

        classifier = DummyClassifier(strategy="prior", random_state=42) if len(unique) < 2 else RandomForestClassifier(
            n_estimators=300, max_depth=14, min_samples_leaf=2, class_weight="balanced",
            random_state=42, n_jobs=-1,
        )
        self.classifier = Pipeline([("features", DictVectorizer(sparse=True)), ("model", classifier)])
        self.classifier.fit(x, y)
        self.training_rows = len(clean)
        self.training_key = training_key or self._training_identity(clean)
        self.classes = list(getattr(classifier, "classes_", unique))
        self.feature_names = list(self.classifier.named_steps["features"].get_feature_names_out())

        targets: list[float] = []
        for row in clean:
            amount = max(0.0, self._finite_float(row.get("amount", 0)))
            recovered_amount = row.get("recovered_amount")
            recovery_rate = row.get("recovery_rate")
            recovered_amount_number = self._finite_float(recovered_amount, float("nan")) if recovered_amount not in (None, "") else float("nan")
            recovery_rate_number = self._finite_float(recovery_rate, float("nan")) if recovery_rate not in (None, "") else float("nan")
            if math.isfinite(recovered_amount_number):
                target = max(0.0, min(amount, recovered_amount_number))
            elif math.isfinite(recovery_rate_number):
                target = amount * max(0.0, min(1.0, recovery_rate_number))
            else:
                target = amount if bool(row.get("is_recoverable")) else 0.0
            targets.append(target)
        self.regressor = Pipeline([
            ("features", DictVectorizer(sparse=True)),
            ("model", RandomForestRegressor(
                n_estimators=250, max_depth=14, min_samples_leaf=2,
                random_state=42, n_jobs=-1,
            )),
        ])
        self.regressor.fit(x, targets)
        self.training_metrics = self._holdout_metrics(clean, y, unique)
        return self.status()

    def _holdout_metrics(self, rows: list[dict[str, Any]], labels: list[str], unique: list[str]) -> dict[str, Any]:
        if len(rows) < 30 or len(unique) < 2:
            return {"holdout_available": False, "reason": "Need >=30 rows and both classes"}
        try:
            train_rows, test_rows, train_y, test_y = train_test_split(
                rows, labels, test_size=0.20, random_state=42, stratify=labels,
            )
            model = Pipeline([
                ("features", DictVectorizer(sparse=True)),
                ("model", RandomForestClassifier(
                    n_estimators=250, max_depth=14, min_samples_leaf=2,
                    class_weight="balanced", random_state=42, n_jobs=-1,
                )),
            ])
            train_x = [self._features(r) for r in train_rows]
            test_x = [self._features(r) for r in test_rows]
            model.fit(train_x, train_y)
            predictions = model.predict(test_x)
            probabilities = model.predict_proba(test_x)
            classes = list(model.named_steps["model"].classes_)
            positive_index = classes.index("recoverable")
            positive_y = [1 if label == "recoverable" else 0 for label in test_y]
            predicted_positive = [1 if label == "recoverable" else 0 for label in predictions]
            return {
                "holdout_available": True,
                "test_rows": len(test_rows),
                "accuracy": round(float(accuracy_score(test_y, predictions)), 4),
                "precision": round(float(precision_score(positive_y, predicted_positive, zero_division=0)), 4),
                "recall": round(float(recall_score(positive_y, predicted_positive, zero_division=0)), 4),
                "f1": round(float(f1_score(positive_y, predicted_positive, zero_division=0)), 4),
                "roc_auc": round(float(roc_auc_score(positive_y, probabilities[:, positive_index])), 4),
            }
        except Exception as exc:
            return {"holdout_available": False, "reason": f"validation_unavailable:{exc.__class__.__name__}"}

    def predict_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.classifier is None:
            raise RuntimeError("No uploaded dataset has trained the ML model yet.")
        if not rows:
            return []
        x = [self._features(row) for row in rows]
        probabilities = self.classifier.predict_proba(x)
        classes = [str(label) for label in self.classifier.named_steps["model"].classes_]
        expected = self.regressor.predict(x) if self.regressor is not None else [None] * len(rows)
        results: list[dict[str, Any]] = []
        for i, probability_row in enumerate(probabilities):
            probability_map = {label: float(prob) for label, prob in zip(classes, probability_row)}
            recoverable_probability = probability_map.get("recoverable", 0.0)
            amount = max(0.0, self._finite_float(rows[i].get("amount", 0)))
            expected_amount = None if expected[i] is None else round(min(amount, max(0.0, self._finite_float(expected[i]))), 2)
            results.append({
                "predicted_label": "recoverable" if recoverable_probability >= 0.5 else "not_recoverable",
                "recoverability_probability": round(recoverable_probability, 4),
                "confidence": round(float(max(probability_map.values())), 4),
                "expected_recovery_amount": expected_amount,
                "expected_recovery_rate": None if expected_amount is None or amount <= 0 else round(expected_amount / amount, 4),
                "model_version": self.version,
                "training_rows": self.training_rows,
                "training_key": self.training_key,
            })
        return results

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        return self.predict_many([row])[0]

    def status(self) -> dict[str, Any]:
        algorithm = self.classifier.named_steps["model"].__class__.__name__ if self.classifier else None
        return {
            "trained": self.classifier is not None,
            "algorithm": algorithm,
            "training_rows": self.training_rows,
            "training_key": self.training_key,
            "classes": self.classes,
            "model_version": self.version,
            "feature_count": len(self.feature_names),
            "training_metrics": self.training_metrics,
            "outputs": ["recoverability_probability", "expected_recovery_amount", "expected_recovery_rate"],
        }


ml_model = RecoveryMLModel()
