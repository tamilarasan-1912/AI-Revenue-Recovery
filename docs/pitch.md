# RecoverAI — 5-minute pitch

## 0:00–0:35 — The problem
A failed payment is not necessarily lost revenue. It may be a temporary bank problem, insufficient funds, a customer who needs another payment route, or a high-risk event that should never be retried. Most systems stop at “payment failed”. RecoverAI treats the failure as a recovery decision.

## 0:35–1:10 — The solution
RecoverAI detects revenue at risk, diagnoses the failure, chooses a bounded intervention and records the complete outcome. The key design principle is: **AI proposes; deterministic policy controls execution.**

## 1:10–2:00 — The agentic workflow
The Risk Agent classifies the failure and estimates revenue at risk. The Strategy Agent chooses among retry, payment link, wait, human escalation or stop. Outputs are structured and validated. The model has no execution authority.

## 2:00–2:45 — The safety gate
Every recommendation passes through a deterministic Policy Engine. Fraud stops recovery. Retry budgets stop repeated attempts. Low confidence goes to human review. Low expected value can stop an intervention. Unsupported actions are blocked.

## 2:45–3:35 — Execution and idempotency
The executor uses a deterministic logical idempotency key. Duplicate webhook events are ignored, and duplicate logical executions cannot silently create a second recovery action. The current demo execution boundary is simulation-only, so no real money moves during judging.

## 3:35–4:25 — Evidence, not claims
The Simulation Lab evaluates a payment-failure cohort against a blind-retry baseline. Headline outputs are revenue at risk, recovered revenue, recovery rate, unnecessary actions, human escalations and unsafe actions blocked. Metrics must be generated from the actual cohort rather than hard-coded.

## 4:25–4:50 — Razorpay integration
RecoverAI accepts Razorpay webhook events and verifies the webhook signature when the configured secret is present. The execution boundary is separated from the AI layer, so a Razorpay Test Mode adapter can be connected without giving the model permission to bypass policy.

## 4:50–5:00 — Closing
RecoverAI is a bounded revenue-recovery workflow: **detect → diagnose → decide → policy-gate → execute → measure → audit.** The goal is to recover more legitimate revenue while making unsafe automation difficult by design.
