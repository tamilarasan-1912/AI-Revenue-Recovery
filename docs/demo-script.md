# RecoverAI — 5-minute Track 03 demo script

## 0:00–0:30 — Open the control room

Open the deployed RecoverAI control center and state clearly: **simulation mode is the default and moves no real money**.

Point to the five headline metrics: revenue at risk, recovered revenue, recovery rate, unsafe actions blocked and human escalations.

## 0:30–1:15 — Explain the decision pipeline

Show:

`Razorpay webhook → Risk Agent → Diagnosis/Strategy → Policy Engine → Executor → Audit Log`

Say: **"The LLM proposes. The deterministic policy authorizes. The executor never accepts an AI decision directly."**

Open **Policies** briefly and show the actual policy version, retry budget and confidence threshold.

## 1:15–2:10 — Show policy decisions, not just a happy path

Open **Recovery Control** and create demo scenarios until you see:

1. `BANK_TIMEOUT_ALLOW` → `ALLOW` → bounded `RETRY` → execute.
2. `FRAUD_STOP` → `STOP` → no execute button.
3. `RETRY_EXHAUSTION_STOP` → `STOP` → no execute button.
4. `LOW_CONFIDENCE_HUMAN_REVIEW` → `HUMAN_REVIEW` → open Human Review.

The important point is that the UI reads confidence and policy output from the backend. It does not display invented confidence percentages or a hardcoded `ALLOW` state.

## 2:10–2:50 — Human review

Open **Human Review** and approve or reject a low-confidence case.

Show that approval executes through the same bounded executor and that rejection produces `REJECTED_BY_HUMAN` in the audit trail.

## 2:50–3:20 — Webhook and idempotency safety

Explain that the webhook handler validates `X-Razorpay-Signature` when a webhook secret is configured and uses the Razorpay event identifier for duplicate-event detection.

Then open **Resilience Lab** and run the synthetic checks. Show:

- retry exhaustion → `STOP`
- duplicate execution → `PROTECTED`

This is a deliberate reliability proof, not a UI animation.

## 3:20–4:10 — Run the evidence experiment

Open **Simulation Lab**.

First run one seed if you want to demonstrate reproducibility. Then click **Run final evidence**.

The UI runs **5 seeds × 10,000 synthetic transactions** and displays:

- baseline recovery rate
- RecoverAI recovery rate
- mean incremental revenue
- standard deviation
- mean improvement
- human-review rate
- unsafe block rate

**Do not memorize or invent the numbers. Run the benchmark immediately before recording the pitch.**

Important wording: the benchmark's recovered revenue is a **synthetic evaluation outcome**, not live money collected from Razorpay.

## 4:10–4:40 — Show payment state and auditability

Open **Payments** and show the payment records created by the demo scenarios.

Open **Audit Log** and export the visible events. Point out the chain from event → policy → review/execution → outcome.

## 4:40–5:00 — Close

Say:

> "RecoverAI does not give an LLM a payment button. It turns failed payments into bounded, measurable recovery decisions, with deterministic stopping rules, compliant escalation, idempotent execution and an auditable outcome."

### Optional Razorpay Test Mode proof

If `ENABLE_RAZORPAY_TEST_ACTIONS=true` and valid Test Mode credentials are configured, demonstrate the Test Mode adapter. Keep live credentials disabled. Never claim that a synthetic benchmark is live recovered revenue.
