# RecoverAI — 5-minute Track 03 demo script

## 0:00–0:30 — Open the control room

Run `docker compose up --build`, open `http://localhost:3000`, and state clearly: **simulation mode is the default and moves no real money**.

Point to the five headline metrics: revenue at risk, recovered revenue, recovery rate, unsafe actions blocked and human escalations.

## 0:30–1:15 — Explain the decision pipeline

Show:

`Razorpay webhook → Risk Agent → Strategy Agent → Policy Engine → Executor → Audit Log`

Say: **"The LLM proposes. The deterministic policy authorizes. The executor never accepts an AI decision directly."**

## 1:15–2:05 — Show three failure cases

Use these scenarios:

1. `bank_timeout`, retry count 0 → bounded `RETRY`.
2. `fraud_suspected` → deterministic `STOP`.
3. retry count 3 → deterministic `STOP`.
4. Optional: low-confidence recommendation → `HUMAN_REVIEW`.

The important point is not that the AI always succeeds; it is that unsafe recommendations are constrained by policy.

## 2:05–2:45 — Demonstrate Razorpay webhook safety

The webhook handler validates the raw body against `X-Razorpay-Signature` when a webhook secret is configured and uses `X-Razorpay-Event-Id` for duplicate-event detection.

Razorpay documents that duplicate webhook delivery can occur and that `payment.failed` can be followed by a later `payment.captured` event. RecoverAI handles both cases.

## 2:45–3:20 — Demonstrate idempotency

Send the same event twice. The second delivery should return `duplicate_event`.

Then explain that a recovery case/action maps to a deterministic idempotency key, so a retry of the same logical execution cannot silently create a second action.

## 3:20–4:15 — Run the evidence experiment

Open **Simulation Lab** and run **10,000 events**.

Use the generated values for:

- revenue at risk
- blind-retry recovered revenue
- RecoverAI recovered revenue
- incremental revenue
- improvement percentage
- human-review rate
- unsafe actions blocked

**Do not memorize or invent these numbers. Run the benchmark immediately before recording the pitch.**

Important wording: the benchmark's "recovered revenue" is a **synthetic evaluation outcome**, not live money collected from Razorpay.

## 4:15–4:45 — Show auditability

Open **Audit Log** and show the chain from event to outcome.

Point out that every recovery decision can be explained through the event, risk/strategy output, policy decision, action and final outcome.

## 4:45–5:00 — Close

Say:

> "RecoverAI does not give an LLM a payment button. It turns failed payments into bounded, measurable recovery decisions, with deterministic stopping rules, compliant escalation and an auditable outcome."

### Optional Test Mode proof

If Test Mode credentials are configured and `ENABLE_RAZORPAY_TEST_ACTIONS=true`, demonstrate a `PAYMENT_LINK` action and show the generated Test Mode link. Keep live credentials disabled.
