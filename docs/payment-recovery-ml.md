# RecoverAI payment-recovery ML design

## Research basis

RecoverAI's recovery policy is based on documented payment-recovery practices from Stripe and Razorpay:

1. **Classify the failure before retrying.** Razorpay exposes structured error fields such as `source`, `step`, and `reason`, and documents different next steps for timeout, authentication, insufficient funds, expired cards, blocked instruments, and risk failures.
2. **Use intelligent, bounded retries for temporary failures.** Stripe describes Smart Retries as ML-driven retry timing based on customer, card, charge, and temporal signals. Razorpay documents automatic retry behaviour for recurring-payment failures.
3. **Do not blindly retry hard/lifecycle failures.** Expired, closed, stolen, or blocked instruments should move to a payment-method-update or alternate-payment flow.
4. **Use customer-assisted recovery.** Payment links and billing-detail updates are appropriate fallbacks when the original instrument cannot be safely recovered by another automatic attempt.
5. **Stop on fraud/risk signals.** Risk-related failures should not be repeatedly retried.
6. **Measure recovery against actual outcomes.** The uploaded CSV's `is_recoverable` field is the supervised target; it is never used as an input feature.

## ML architecture

The uploaded CSV trains a `RandomForestClassifier` to estimate:

`P(payment is recoverable | failure reason, amount, retry history, optional payment context)`

The current minimum features are:

- `failure_reason`
- `amount`
- `retry_count`
- engineered `amount_log`
- engineered `retry_pressure`

The model also accepts optional fields when they are present in a training payload, including payment method, decline code, error source/step, recurring status, authentication requirement, card-expiry age, customer tenure, previous success rate, days past due, hour of day, and day of week.

## How ML controls recovery

The model does **not** directly execute a payment. Its probability is passed to the recovery playbook:

- `< 0.30`: automatic retry is rejected; use a payment link/alternate method where appropriate.
- `0.30–0.65`: human review for uncertain soft-decline cases.
- `>= 0.65`: a classified soft decline can enter the bounded retry schedule.
- hard/lifecycle failures: payment-method update/payment link rather than repeated same-instrument retries.
- authentication-required failures: authenticated checkout/payment link.
- fraud signals: STOP.

The policy engine remains the final authorization boundary.

## Training behaviour

Every uploaded dataset retrains the model. For datasets with at least 30 rows and both classes, RecoverAI also computes a held-out accuracy and ROC-AUC score. For smaller or one-class datasets, the application reports that a meaningful holdout metric is unavailable instead of fabricating a score.

## Important limitation

The current dataset schema has a recoverability label but does not contain historical **retry timestamp + retry outcome** pairs. Therefore RecoverAI does not claim to have trained a true optimal-retry-time model. Retry timing is currently a research-backed, configurable policy (24/72/168 hours by default). Once historical retry outcomes are collected, a separate model can be trained to predict `P(success | retry_time, context)` and optimize the next retry window.

## Sources

- Stripe, Payments recovered by Stripe: https://support.stripe.com/questions/payments-recovered-by-stripe
- Stripe, How we built Smart Retries: https://stripe.com/blog/how-we-built-it-smart-retries
- Stripe, Payment processing best practices: https://stripe.com/guides/payment-processing
- Razorpay, Cards error codes: https://razorpay.com/docs/errors/payments/cards/
- Razorpay, Payment retries: https://razorpay.com/docs/payments/subscriptions/payment-retries/
- Razorpay, Failed Payment Recovery: https://razorpay.com/blog/razorpay-failed-payment-recovery/
- Razorpay, Intelligent Payment Retry: https://razorpay.com/blog/?p=15250
