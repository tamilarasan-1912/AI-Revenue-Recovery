"""Research-backed payment recovery playbook.

This module models the operational recovery sequence used by modern payment
platforms: classify the failure, distinguish retryable soft declines from
non-retryable/hard declines, use bounded retries with a rescue window, then
switch to customer-action/payment-link recovery when retries are exhausted.

Provider-specific retry schedules remain configurable; this is a safe
simulation policy and does not itself move real money.
"""
from __future__ import annotations

from typing import Any

DEFAULT_RETRY_DELAYS_HOURS = (24, 72, 168)
DEFAULT_RESCUE_WINDOW_DAYS = 30


def _reason(value: Any) -> str:
    return str(value or "unknown").strip().lower().replace("-", "_").replace(" ", "_")


def build_recovery_plan(payment: dict[str, Any], *, max_retries: int = 3, retry_delays_hours: tuple[int, ...] = DEFAULT_RETRY_DELAYS_HOURS, rescue_window_days: int = DEFAULT_RESCUE_WINDOW_DAYS) -> dict[str, Any]:
    reason = _reason(payment.get("failure_reason"))
    retries = max(0, int(payment.get("retry_count", 0) or 0))
    fraud = bool(payment.get("fraud_signal")) or "fraud" in reason

    hard_declines = {"card_closed", "closed_account", "invalid_card", "expired_card", "lost_card", "stolen_card", "do_not_honor", "permanent_decline", "invalid_account", "account_closed", "mandate_cancelled"}
    authentication = {"authentication_required", "3ds_required", "3d_secure_required", "customer_action_required", "issuer_authentication_required"}
    soft_declines = {"insufficient_funds", "bank_timeout", "timeout", "temporary_bank_degradation", "issuer_unavailable", "temporary_decline", "processing_error", "network_error", "gateway_timeout", "try_again_later"}

    if fraud:
        return {"recovery_status": "STOP", "failure_class": "fraud_suspected", "retryable": False, "recommended_action": "STOP", "customer_action_required": False, "payment_link_fallback": False, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "risk_stop", "reason": "Fraud/risk signals should not be retried automatically.", "steps": ["Stop automatic recovery", "Flag for risk review", "Do not send repeated authorization attempts"]}

    if reason in hard_declines:
        return {"recovery_status": "CUSTOMER_ACTION", "failure_class": "hard_decline", "retryable": False, "recommended_action": "PAYMENT_LINK", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "payment_method_update", "reason": "The failure is unlikely to succeed by repeatedly charging the same payment instrument.", "steps": ["Do not retry the same instrument", "Ask the customer to update or replace the payment method", "Send a secure payment link", "Escalate if the customer cannot complete payment"]}

    if reason in authentication:
        return {"recovery_status": "CUSTOMER_ACTION", "failure_class": "authentication_required", "retryable": False, "recommended_action": "PAYMENT_LINK", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "customer_authentication", "reason": "The customer/issuer must complete an authentication step before payment can succeed.", "steps": ["Request customer authentication", "Send the customer to an authenticated checkout/payment link", "Retry only after the customer action produces a new payment attempt"]}

    if reason in soft_declines:
        if retries >= max_retries:
            return {"recovery_status": "CUSTOMER_ACTION", "failure_class": "retry_exhausted", "retryable": False, "recommended_action": "PAYMENT_LINK", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "retry_exhausted", "reason": "The bounded retry budget is exhausted; switch to customer-assisted recovery.", "steps": ["Stop automatic retries", "Send a secure payment link or payment-method-update flow", "Escalate unresolved high-value cases"]}
        delay_index = min(retries, len(retry_delays_hours) - 1)
        delay = retry_delays_hours[delay_index]
        return {"recovery_status": "RETRY_SCHEDULED", "failure_class": "soft_decline", "retryable": True, "recommended_action": "RETRY", "customer_action_required": False, "payment_link_fallback": True, "next_retry_in_hours": delay, "rescue_window_days": rescue_window_days, "recovery_stage": "bounded_retry", "reason": "The failure may be temporary, so use a bounded retry schedule rather than repeated immediate charges.", "steps": [f"Wait {delay} hours before the next attempt", "Retry once", "Stop if the retry budget or rescue window is exhausted", "Use a payment link if retries fail"]}

    return {"recovery_status": "HUMAN_REVIEW", "failure_class": "unclassified_failure", "retryable": False, "recommended_action": "HUMAN_ESCALATION", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "manual_diagnosis", "reason": "The failure reason is not safely classified for automatic recovery.", "steps": ["Review issuer/gateway refusal details", "Avoid blind retries", "Use a payment link or payment-method update after diagnosis"]}


def attach_recovery_plan(payment: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    result = dict(payment)
    result["recovery_plan"] = build_recovery_plan(payment, **kwargs)
    return result
