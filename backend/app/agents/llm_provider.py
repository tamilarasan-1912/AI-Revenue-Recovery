"""LLM boundary for RecoverAI.

The provider is deliberately fail-safe: if no external model is configured,
we use a deterministic, context-aware evaluator so the demo remains runnable.
The model never receives permission to execute financial actions.
"""
import json
import os
import urllib.request
from typing import Any


ALLOWED_ACTIONS = {"RETRY", "PAYMENT_LINK", "HUMAN_ESCALATION", "STOP", "WAIT"}


def _deterministic(prompt: str) -> dict[str, Any]:
    try:
        data = json.loads(prompt.split("|", 1)[1])
    except Exception:
        data = {}
    amount = float(data.get("amount", 0) or 0)
    reason = str(data.get("failure_reason", "unknown")).lower()
    retries = int(data.get("retry_count", 0) or 0)
    recoverable = data.get("is_recoverable", None)

    if "fraud" in reason:
        return {"revenue_at_risk": amount, "risk_score": 0.99, "failure_class": "fraud_suspected", "confidence": 0.97}
    if "insufficient" in reason:
        risk = 0.72 if retries < 2 else 0.86
        return {"revenue_at_risk": amount, "risk_score": risk, "failure_class": "insufficient_funds", "confidence": 0.90}
    if "timeout" in reason or "bank" in reason:
        return {"revenue_at_risk": amount, "risk_score": 0.82, "failure_class": "temporary_bank_degradation", "confidence": 0.94}
    return {"revenue_at_risk": amount, "risk_score": 0.60, "failure_class": "unknown_payment_failure", "confidence": 0.68}


def _strategy(data: dict[str, Any]) -> dict[str, Any]:
    amount = float(data.get("amount", 0) or 0)
    reason = str(data.get("failure_reason", "unknown")).lower()
    retries = int(data.get("retry_count", 0) or 0)
    confidence = float(data.get("risk_confidence", 0.5) or 0.5)
    if "fraud" in reason:
        action = "STOP"
    elif retries >= 3:
        action = "HUMAN_ESCALATION"
    elif "timeout" in reason or "bank" in reason:
        action = "RETRY" if retries < 2 else "PAYMENT_LINK"
    elif "insufficient" in reason:
        action = "PAYMENT_LINK"
    else:
        action = "HUMAN_ESCALATION"
    probability = 0.80 if action in {"RETRY", "PAYMENT_LINK"} else 0.35
    return {"recommended_action": action, "expected_recovery_value": round(amount * probability, 2), "confidence": min(0.96, max(0.55, confidence))}


def _external_openai_compatible(prompt: str) -> dict[str, Any] | None:
    endpoint = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")
    if not endpoint or not api_key or not model:
        return None
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": "Return only valid JSON. Never execute financial actions."}, {"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode()
    request = urllib.request.Request(endpoint + "/chat/completions", data=body, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode())
    return json.loads(payload["choices"][0]["message"]["content"])


class RecoveryLLMProvider:
    def generate_structured(self, prompt: str, schema: dict) -> dict[str, Any]:
        result = _external_openai_compatible(prompt) if os.getenv("LLM_PROVIDER", "deterministic") == "openai_compatible" else None
        if result is None:
            result = _deterministic(prompt) if prompt.startswith("risk|") else _strategy(json.loads(prompt.split("|", 1)[1]))
        if not isinstance(result, dict):
            raise ValueError("AI response must be an object")
        return result


def get_llm_provider() -> RecoveryLLMProvider:
    return RecoveryLLMProvider()


llm_provider = get_llm_provider()
