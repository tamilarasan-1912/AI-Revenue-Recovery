# RecoverAI

**AI Revenue Recovery & Churn Prevention Platform for Razorpay merchants.**

RecoverAI turns a failed payment into a bounded recovery case: **detect revenue at risk → diagnose the failure → recommend an intervention → apply deterministic policy → execute safely → measure the outcome → audit every decision.**

## Razorpay Track 03 alignment

Track 03 asks builders to find revenue slipping away and win it back with a bounded recovery workflow, measured batch recovery, compliant escalation, stopping rules and an audit trail. RecoverAI focuses on payment-failure recovery and makes the control boundary explicit: **AI proposes; deterministic policy authorizes.**

## Architecture

```text
Razorpay Test Mode / webhook
          ↓
   Signature validation
          ↓
 Duplicate event protection
          ↓
      Risk Agent
          ↓
    Strategy Agent
          ↓
   Deterministic Policy
     ↙      ↓       ↘
 ALLOW   HUMAN     STOP/BLOCK
   ↓     REVIEW        ↓
Safe executor      Audit log
   ↓
Simulation/Test adapter
   ↓
Outcome + recovery metrics
```

## AI and safety

- Context-aware risk classification using amount, failure reason and retry history.
- Context-aware intervention selection across RETRY, PAYMENT_LINK, HUMAN_ESCALATION, WAIT and STOP.
- Optional OpenAI-compatible structured model endpoint through environment variables.
- Deterministic fallback keeps the demo runnable without an API key.
- The model never receives permission to execute financial actions.
- Fraud signals stop recovery before lower-priority rules can authorize an action.
- Retry limits, confidence thresholds and economic thresholds are enforced by backend policy.
- Execution keys are deterministic so duplicate delivery cannot create a new logical execution.

## Razorpay boundary

The repository verifies Razorpay webhook signatures when `RAZORPAY_WEBHOOK_SECRET` is configured. Recovery execution is deliberately labeled **SIMULATION** in the demo and does not move real money. A production/Test Mode adapter can be connected at the execution boundary without allowing the LLM to bypass policy.

## Batch evaluation

The simulation generates failed-payment cohorts and compares RecoverAI with a blind-retry baseline. Results should be generated from the dataset at runtime; do not hard-code benchmark claims. The evaluation should report revenue at risk, recovered revenue, recovery rate, unnecessary actions, human escalations and unsafe actions blocked.

## Quick start

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000`.

Backend tests:

```bash
cd backend
pytest -q
```

## Environment variables

```text
DATABASE_URL=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
LLM_PROVIDER=deterministic
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

Never commit `.env` or API credentials.

## Demo scenarios

1. Temporary bank timeout → retry/payment-link recovery.
2. Insufficient funds → payment-link intervention.
3. Fraud suspected → deterministic STOP.
4. Retry budget exhausted → deterministic STOP.
5. Low AI confidence → HUMAN_REVIEW.
6. Duplicate webhook → ignored by event id.
7. Duplicate logical execution → same idempotency key and no second execution.

## Project status

This is a buildathon prototype. The safe simulation adapter is intentional; it must not be described as live-money recovery. Any live/Test Mode adapter must preserve webhook verification, policy enforcement and auditability.
