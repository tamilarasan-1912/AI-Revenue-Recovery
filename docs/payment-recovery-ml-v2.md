# AI Payment Recovery — Behaviour-Based ML

This module extends RecoverAI from failure classification into **payment recovery propensity prediction**, expected recovery estimation, and policy-guided recovery recommendations.

## Model outputs

For each failed or outstanding payment, the model predicts:

- `recoverability_probability`: probability that the payment is recoverable under the learned historical pattern.
- `expected_recovery_amount`: estimated amount likely to be recovered.
- `expected_recovery_rate`: expected recovery amount divided by the payment amount.

The deterministic recovery playbook then uses the probability to select a safe next step. The ML model does **not** execute charges and cannot bypass the policy/safety layer.

## Behaviour features

The training payload supports payment and customer-history signals such as:

- payment method and decline/error context
- retry count and engineered retry pressure
- transaction amount and log-transformed amount
- recurring-payment flag
- authentication requirement
- card-expiry age
- customer tenure
- previous payment success/failure/delay counts
- historical payment success rate
- average payment delay
- days past due
- outstanding amount
- reminder count and reminder response rate
- hour/day timing features

These fields allow the model to learn patterns such as customers who usually pay after a reminder, repeated temporary failures, or high retry pressure.

## Training

The uploaded CSV remains the supervised source. `is_recoverable` is the classification target and is never included as an input feature.

The classifier uses `RandomForestClassifier` and the expected-recovery estimator uses `RandomForestRegressor`. Categorical values are encoded through `DictVectorizer`, allowing older datasets with the original four required columns to continue working.

If a dataset contains `recovered_amount` or `recovery_rate`, those values are used to train the recovery-amount estimator. When only the binary recoverability label exists, the estimator uses a transparent proxy of `amount` for recoverable rows and `0` otherwise; this should be treated as an expected-value proxy until real transaction-level recovery outcomes are collected.

For datasets with at least 30 rows and both classes, the API reports held-out accuracy and ROC-AUC for the classifier. No fabricated validation score is returned for smaller or one-class datasets.

## Recovery decision logic

The probability is passed to the existing research-backed recovery playbook:

- `< 0.30`: avoid automatic retry; prefer a secure payment link/alternate method where appropriate.
- `0.30–0.65`: treat as uncertain and route to human review for soft-decline cases.
- `>= 0.65`: a classified soft decline may enter the bounded retry schedule.
- hard/lifecycle/authentication failures still require customer action rather than repeated blind retries.
- fraud/risk signals stop automated recovery.

This keeps ML as a **decision-support signal**, while the policy engine remains the final authorization boundary.

## API examples

After a dataset has been imported/trained:

`POST /api/simulation/predict-recovery`

Example payload:

```json
{
  "payment_id": "pay_1024",
  "amount": 750,
  "failure_reason": "insufficient_funds",
  "retry_count": 1,
  "payment_method": "upi",
  "previous_payment_success_rate": 0.92,
  "previous_delayed_payment_count": 2,
  "average_payment_delay_days": 1.5,
  "reminder_count": 1,
  "reminder_response_rate": 0.8,
  "days_past_due": 2,
  "outstanding_amount": 750
}
```

The response contains both the ML prediction and the final policy-guided recovery plan.

For batch scoring use `POST /api/simulation/predict-batch` with `{ "rows": [...] }`.

## Feedback loop

The intended production flow is:

`payment event → feature aggregation → ML score → policy decision → recovery action → actual outcome → training dataset → periodic retraining`

The current service retrains from uploaded datasets. A production implementation should persist retry timestamps, retry outcomes, customer-action outcomes, and recovered amounts so that the next model version can learn **time-to-recovery** and **best-action** directly instead of relying on fixed policy intervals.

## Research basis

The design follows documented payment-recovery practices: classify failures before retrying; use bounded/intelligent retries for temporary failures; move hard/lifecycle/authentication failures to customer-assisted payment-method recovery; stop for fraud/risk; and measure actual recovery outcomes. See the companion document `docs/payment-recovery-ml.md` for the original source list and provider references.
