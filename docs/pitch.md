# RecoverAI — 5-minute Razorpay Track 03 pitch

## 0:00–0:35 — Problem

"A failed payment is not necessarily lost revenue. It may be a temporary bank problem, insufficient funds, a customer who needs another payment route, or a risky event that should never be retried. Most systems stop at 'payment failed'. RecoverAI asks the next question: **what is the safest way to recover this revenue?**"

## 0:35–1:10 — Solution

"RecoverAI is an AI revenue-recovery control plane for Razorpay merchants. It takes a failed-payment event, estimates revenue at risk, diagnoses the failure, recommends an intervention, applies deterministic safety policy, executes a bounded workflow, measures the result and writes an audit trail."

"The central architecture is simple: **AI proposes; policy controls.**"

## 1:10–2:00 — Agentic workflow

"First, the Risk Agent looks at the payment amount, failure reason and retry history. It produces structured risk information: revenue at risk, risk score, failure class and confidence."

"Then the Strategy Agent uses that context to select a recovery action: retry, payment link, human escalation, wait or stop. The output is schema-checked before anything reaches the execution layer."

"This is important: the model never gets a tool that can directly move money."

## 2:00–2:45 — Safety gate

"Every recommendation enters the deterministic Policy Engine. Fraud signals force a stop. Retry counts are bounded. Low confidence becomes human review. Waiting is not treated as an immediate money action. Low expected recovery value can also stop an intervention. Unsupported actions are blocked."

"So if the AI is wrong, the system still has a second line of defense."

## 2:45–3:25 — Razorpay integration

"The system consumes Razorpay payment webhooks and validates the raw webhook signature when the webhook secret is configured. It also uses the Razorpay event ID for duplicate-event protection."

"We explicitly handle a late successful payment after an earlier failure, because payment state can legitimately change after a failure event."

"For judging, simulation is the default. If we enable it with Test Mode credentials, the bounded payment-link adapter can create a Razorpay Test Mode Payment Link. Live-money execution is not enabled."

## 3:25–4:10 — Evidence

"Now we need evidence, not a dashboard full of claims. The Simulation Lab generates a reproducible synthetic cohort and compares RecoverAI against blind retry. The default benchmark is 10,000 payment-failure events."

"The benchmark reports recovered revenue, recovery rate, incremental revenue, improvement versus baseline, human-review rate and unsafe actions blocked."

**Important:** replace this section's spoken figures with the actual output generated immediately before recording. Never invent benchmark numbers.

## 4:10–4:40 — Auditability and failure handling

"Every decision has a chain: webhook event, risk analysis, strategy, policy decision, execution outcome and audit record. Duplicate webhook delivery is ignored. Duplicate logical execution uses the same deterministic idempotency key. Fraud and exhausted retries stop automatically. Low-confidence cases are escalated instead of blindly executed."

## 4:40–5:00 — Closing

"Razorpay Track 03 asks us to do more than detect revenue leakage. RecoverAI closes the loop: **detect → diagnose → decide → policy-gate → recover → measure → audit.**"

"The differentiator is not simply an LLM choosing an action. It is an AI recovery agent surrounded by deterministic financial safety controls and measurable batch evidence."
