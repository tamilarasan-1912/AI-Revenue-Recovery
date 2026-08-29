"""Deterministic root-cause diagnosis boundary.

The diagnosis layer normalizes payment evidence into a typed diagnosis. It can
later be backed by an LLM, but the returned classes remain bounded and are never
execution commands.
"""

from typing import Any


DIAGNOSIS_CLASSES = {
    "temporary_bank_degradation",
    "insufficient_funds",
    "authentication_required",
    "payment_method_invalid",
    "fraud_suspected",
    "hard_decline",
    "unknown_payment_failure",
}


def diagnose_failure(payment_data: dict[str, Any]) -> dict[str, Any]:
    reason = str(payment_data.get("failure_reason", "")).lower()
    method = str(payment_data.get("payment_method", "")).lower()
    retry_count = int(payment_data.get("retry_count", 0) or 0)

    if any(x in reason for x in ("fraud", "stolen", "lost_card", "security")):
        diagnosis = "fraud_suspected"
        confidence = 0.97
    elif any(x in reason for x in ("authentication", "3ds", "auth_required", "otp")):
        diagnosis = "authentication_required"
        confidence = 0.94
    elif any(x in reason for x in ("expired", "invalid", "payment_method")):
        diagnosis = "payment_method_invalid"
        confidence = 0.93
    elif any(x in reason for x in ("insufficient", "funds", "balance")):
        diagnosis = "insufficient_funds"
        confidence = 0.91
    elif any(x in reason for x in ("timeout", "bank", "issuer", "temporary", "network")):
        diagnosis = "temporary_bank_degradation"
        confidence = 0.94
    elif any(x in reason for x in ("decline", "do_not_honor", "hard")):
        diagnosis = "hard_decline"
        confidence = 0.88
    else:
        diagnosis = "unknown_payment_failure"
        confidence = 0.65

    evidence = [
        f"failure_reason={payment_data.get('failure_reason', 'unknown')}",
        f"payment_method={method or 'unknown'}",
        f"retry_count={retry_count}",
    ]
    return {
        "diagnosis_class": diagnosis,
        "confidence": confidence,
        "evidence": evidence,
        "safe_to_retry": diagnosis == "temporary_bank_degradation" and retry_count < 3,
    }
