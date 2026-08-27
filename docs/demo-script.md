# RecoverAI — 5-minute demo script

## 0:00–0:30 — Open the control room
Run `docker compose up --build`, open `http://localhost:3000`, and point out the Revenue Recovery Control Room. State clearly that this demo uses simulation mode and moves no real money.

## 0:30–1:20 — Explain the decision pipeline
Show: failed payment → Risk Agent → Strategy Agent → deterministic Policy Engine → executor → audit. Emphasize that AI proposes but cannot authorize execution.

## 1:20–2:20 — Show safety behavior
Use three scenarios in the API/webhook demo: a temporary bank timeout, a fraud-suspected payment, and a payment that has exhausted its retry budget. Explain that fraud is stopped, exhausted retries are stopped, and low-confidence decisions can go to human review.

## 2:20–3:10 — Demonstrate idempotency
Send the same webhook event twice. The second event should return `duplicate_event`. Then show that the same recovery case/action maps to the same logical idempotency key, preventing a second logical execution.

## 3:10–4:20 — Run the evidence experiment
Open Simulation Lab and run a cohort of 10,000 events. Compare RecoverAI with the blind-retry baseline. Use the generated metrics: revenue at risk, recovered revenue, recovery rate, unnecessary actions, human escalations and unsafe actions blocked. Do not invent numbers before the run.

## 4:20–5:00 — Close on business impact
Open Audit Log and show the trace from event to outcome. Close with: “RecoverAI does not give an LLM a payment button. It turns failed payments into bounded, measurable recovery decisions, with a deterministic safety gate and an auditable outcome.”
