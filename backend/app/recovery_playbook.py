"""Research-backed, provider-neutral payment recovery playbook.

The research basis is consistent across major payment platforms:
- classify the failure before retrying;
- retry temporary/soft failures at deliberate intervals rather than immediately;
- move card/lifecycle/authentication problems to customer-action flows;
- stop on fraud/high-risk signals and avoid blind retries;
- keep a bounded retry budget and rescue window.

The ML model supplies the recoverability probability used to decide whether an
automatic retry is justified. This module never executes a real payment.
"""
from __future__ import annotations

from typing import Any

DEFAULT_RETRY_DELAYS_HOURS = (24, 72, 168)
DEFAULT_RESCUE_WINDOW_DAYS = 30


def _reason(value: Any) -> str:
    return str(value or "unknown").strip().lower().replace("-", "_").replace(" ", "_")


def _as_bool(value: Any) -> bool:
    """Parse common CSV/API boolean representations without Python truthiness traps."""
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


def build_recovery_plan(payment: dict[str, Any], *, max_retries: int = 3, retry_delays_hours: tuple[int, ...] = DEFAULT_RETRY_DELAYS_HOURS, rescue_window_days: int = DEFAULT_RESCUE_WINDOW_DAYS) -> dict[str, Any]:
    reason = _reason(payment.get("failure_reason"))
    decline_code = _reason(payment.get("decline_code"))
    error_source = _reason(payment.get("error_source"))
    authentication_required = _as_bool(payment.get("authentication_required"))
    retries = max(0, int(payment.get("retry_count", 0) or 0))
    max_retries = max(0, int(max_retries))
    rescue_window_days = max(0, int(rescue_window_days))
    fraud = _as_bool(payment.get("fraud_signal")) or "fraud" in reason or "fraud" in decline_code
    ml_probability = payment.get("ml_recoverability")
    p = None if ml_probability is None else max(0.0, min(1.0, float(ml_probability)))

    # Do-not-honor is intentionally treated as a soft/uncertain decline: it
    # can sometimes recover after customer/bank action and should not be
    # classified as a permanently invalid card.
    hard_declines = {"card_closed", "closed_account", "invalid_card", "expired_card", "card_expired", "lost_card", "stolen_card", "permanent_decline", "invalid_account", "account_closed", "mandate_cancelled", "debit_instrument_blocked"}
    auth_failures = {"authentication_required", "3ds_required", "3d_secure_required", "customer_action_required", "issuer_authentication_required", "authentication_failed", "invalid_otp", "incorrect_otp", "otp_expired"}
    soft_declines = {"insufficient_funds", "bank_timeout", "timeout", "temporary_bank_degradation", "issuer_unavailable", "temporary_decline", "processing_error", "network_error", "gateway_timeout", "try_again_later", "payment_timed_out", "payment_collect_request_expired", "payment_declined", "payment_failed", "do_not_honor", "transaction_limit_exceeded", "card_declined"}

    if fraud:
        return {"recovery_status": "STOP", "failure_class": "fraud_suspected", "retryable": False, "recommended_action": "STOP", "customer_action_required": False, "payment_link_fallback": False, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "risk_stop", "reason": "Fraud/risk signals should not be retried automatically.", "steps": ["Stop automatic recovery", "Flag for risk review", "Do not send repeated authorization attempts"]}

    if authentication_required or reason in auth_failures or decline_code in auth_failures:
        return {"recovery_status": "CUSTOMER_ACTION", "failure_class": "authentication_required", "retryable": False, "recommended_action": "PAYMENT_LINK", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "customer_authentication", "reason": "The issuer/customer requires authentication before a successful payment attempt.", "steps": ["Request customer authentication", "Send the customer to an authenticated checkout/payment link", "Retry only after a new authenticated payment attempt"]}

    if reason in hard_declines or decline_code in hard_declines:
        return {"recovery_status": "CUSTOMER_ACTION", "failure_class": "hard_decline", "retryable": False, "recommended_action": "PAYMENT_LINK", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "payment_method_update", "reason": "The original instrument is unlikely to recover through repeated retries.", "steps": ["Do not repeatedly charge the same instrument", "Ask the customer to update or replace the payment method", "Send a secure payment link", "Escalate unresolved high-value cases"]}

    if reason in soft_declines or decline_code in soft_declines or error_source in {"bank", "gateway", "network"}:
        if p is not None and p < 0.30:
            return {"recovery_status": "CUSTOMER_ACTION", "failure_class": "low_ml_recoverability", "retryable": False, "recommended_action": "PAYMENT_LINK", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "ml_low_probability", "reason": "The trained recovery model estimates a low probability of successful automatic recovery.", "steps": ["Avoid another blind retry", "Offer a secure payment link or alternate payment method", "Escalate if the customer cannot recover the payment"]}
        if p is not None and p < 0.65:
            return {"recovery_status": "HUMAN_REVIEW", "failure_class": "uncertain_ml_recoverability", "retryable": False, "recommended_action": "HUMAN_ESCALATION", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "ml_uncertain", "reason": "The trained model is not confident enough for automatic retry.", "steps": ["Review the failure context", "Offer a payment link/alternate method", "Retry only after review confirms the recovery path"]}
        if retries >= max_retries:
            return {"recovery_status": "CUSTOMER_ACTION", "failure_class": "retry_exhausted", "retryable": False, "recommended_action": "PAYMENT_LINK", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "retry_exhausted", "reason": "The bounded retry budget is exhausted.", "steps": ["Stop automatic retries", "Send a secure payment link or payment-method-update flow", "Escalate unresolved high-value cases"]}
        delay_index = min(retries, max(0, len(retry_delays_hours) - 1))
        delay = retry_delays_hours[delay_index] if retry_delays_hours else 24
        if reason == "insufficient_funds":
            timing_reason = "Insufficient funds are a soft decline; wait for a likely balance replenishment window instead of retrying immediately."
        elif reason in {"timeout", "bank_timeout", "gateway_timeout", "processing_error", "network_error"}:
            timing_reason = "Temporary technical failures are retried after a delay to avoid repeated attempts during the same outage window."
        else:
            timing_reason = "The failure may be recoverable, so use a bounded retry schedule rather than repeated immediate charges."
        return {"recovery_status": "RETRY_SCHEDULED", "failure_class": "soft_decline", "retryable": True, "recommended_action": "RETRY", "customer_action_required": False, "payment_link_fallback": True, "next_retry_in_hours": delay, "rescue_window_days": rescue_window_days, "recovery_stage": "bounded_retry", "reason": timing_reason, "steps": [f"Wait {delay} hours before the next attempt", "Retry once", "Stop if the retry budget or rescue window is exhausted", "Use a payment link if retries fail"]}

    return {"recovery_status": "HUMAN_REVIEW", "failure_class": "unclassified_failure", "retryable": False, "recommended_action": "HUMAN_ESCALATION", "customer_action_required": True, "payment_link_fallback": True, "next_retry_in_hours": None, "rescue_window_days": rescue_window_days, "recovery_stage": "manual_diagnosis", "reason": "The failure reason is not safely classified for automatic recovery.", "steps": ["Review issuer/gateway refusal details", "Avoid blind retries", "Use a payment link or payment-method update after diagnosis"]}


def attach_recovery_plan(payment: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    result = dict(payment)
    result["recovery_plan"] = build_recovery_plan(payment, **kwargs)
    return result
