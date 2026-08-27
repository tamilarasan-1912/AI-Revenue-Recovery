import json
from .llm_provider import llm_provider


def analyze_risk(payment_data: dict) -> dict:
    """Classify payment risk without granting execution authority to the model."""
    result = llm_provider.generate_structured(f"risk|{json.dumps(payment_data, sort_keys=True)}", {})
    required = {"revenue_at_risk", "risk_score", "failure_class", "confidence"}
    if not required.issubset(result):
        raise ValueError("Risk agent returned an incomplete structured result")
    result["fraud_signal"] = result["failure_class"] == "fraud_suspected"
    result["evidence"] = [
        f"failure_reason={payment_data.get('failure_reason', 'unknown')}",
        f"retry_count={payment_data.get('retry_count', 0)}",
        f"amount={payment_data.get('amount', 0)}",
    ]
    return result
