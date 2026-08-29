"""Customer communication layer.

Messages are generated from bounded templates. No customer message can trigger
payment execution; payment links are supplied separately by the executor.
"""

from typing import Any


def generate_recovery_message(payment_data: dict[str, Any], diagnosis: dict[str, Any], action: str, locale: str = "en-IN") -> dict[str, str]:
    amount = float(payment_data.get("amount", 0) or 0)
    name = str(payment_data.get("customer_name") or "there").strip()
    reason = diagnosis.get("diagnosis_class", "unknown_payment_failure")

    if action == "PAYMENT_LINK":
        if reason == "insufficient_funds":
            body = f"Hi {name}, your ₹{amount:,.0f} payment could not be completed because the available balance was insufficient. You can securely complete the payment using the recovery link provided below."
        else:
            body = f"Hi {name}, your ₹{amount:,.0f} payment could not be completed. You can securely complete the payment using the recovery link provided below."
    elif action == "RETRY":
        body = f"Hi {name}, your ₹{amount:,.0f} payment encountered a temporary processing issue. We will retry the payment within the permitted recovery window."
    elif action == "HUMAN_ESCALATION":
        body = f"Hi {name}, we could not safely complete your ₹{amount:,.0f} payment automatically. Our support team will review it and help you complete the payment."
    elif action == "STOP":
        body = f"Hi {name}, we could not safely complete your ₹{amount:,.0f} payment. No further automated payment attempt will be made."
    else:
        body = f"Hi {name}, your ₹{amount:,.0f} payment is being handled within our recovery policy."

    return {
        "locale": locale,
        "channel": "customer_message",
        "subject": "Payment recovery update",
        "body": body,
    }
