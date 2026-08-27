import json
from .llm_provider import llm_provider


def recommend_strategy(payment_data: dict, risk_analysis: dict) -> dict:
    """Recommend an intervention; execution remains controlled by PolicyEngine."""
    context = dict(payment_data)
    context["risk_score"] = risk_analysis.get("risk_score", 0.0)
    context["risk_confidence"] = risk_analysis.get("confidence", 0.0)
    context["failure_class"] = risk_analysis.get("failure_class", "unknown")
    context["fraud_signal"] = risk_analysis.get("fraud_signal", False)
    result = llm_provider.generate_structured(f"strategy|{json.dumps(context, sort_keys=True)}", {})
    if result.get("recommended_action") not in {"RETRY", "PAYMENT_LINK", "HUMAN_ESCALATION", "STOP", "WAIT"}:
        raise ValueError("Strategy agent returned an unsupported action")
    if not 0 <= float(result.get("confidence", 0)) <= 1:
        raise ValueError("Strategy confidence must be between 0 and 1")
    return result
