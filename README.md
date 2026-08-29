# RecoverAI

**AI Revenue Recovery & Churn Prevention Platform for Razorpay merchants.**

RecoverAI turns a failed payment into a bounded recovery case:

**detect revenue at risk → diagnose the failure → recommend an intervention → apply deterministic policy → execute safely → measure the outcome → audit every decision.**

## Architecture

```text
Razorpay Test Mode webhook
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
Simulation / Razorpay Test Mode adapter
   ↓
Outcome + recovery metrics
```

## AI layer

- Context-aware risk classification using amount, failure reason and retry history.
- Context-aware intervention selection across `RETRY`, `PAYMENT_LINK`, `HUMAN_ESCALATION`, `WAIT` and `STOP`.
- Optional OpenAI-compatible structured model endpoint through environment variables.
- Deterministic fallback keeps the prototype runnable without an external API key.
- Structured outputs are validated before policy evaluation.
- The model has **no execution authority**.

## Policy and safety layer

- Fraud signals force `STOP`.
- Retry budget is bounded by `MAX_RETRIES`.
- Low-confidence recommendations route to `HUMAN_REVIEW`.
- `WAIT` is never treated as an immediate money action.
- Low expected recovery value can stop an intervention.
- Every execution gets a deterministic idempotency key.
- Duplicate webhook delivery is detected using Razorpay's event identifier.
- Late `payment.captured` / successful events update an existing failed payment instead of blindly launching another recovery.

## Batch evidence

The Simulation Lab evaluates a synthetic failed-payment cohort against a blind-retry baseline. The benchmark is reproducible using a seed and defaults to **10,000 events**.

The runtime result reports:

- revenue at risk
- recovered revenue
- recovery rate
- incremental revenue
- improvement vs blind retry
- human-review rate
- unsafe actions blocked
- intervention/action distribution

**Benchmark numbers are generated at runtime. They are not hard-coded.**

## Demo scenarios

1. Temporary bank timeout → bounded retry or payment-link recovery.
2. Insufficient funds → payment-link intervention.
3. Fraud suspected → deterministic STOP.
4. Retry budget exhausted → deterministic STOP.
5. Low AI confidence → HUMAN_REVIEW.
6. Duplicate Razorpay webhook → ignored by event ID.
7. Late successful payment after a failure → payment state reconciled.
8. Duplicate logical execution → same idempotency key, no second execution.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000`.

Backend tests:

```bash
cd backend
pytest -q
```

## Environment

```text
DATABASE_URL=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
ENABLE_RAZORPAY_TEST_ACTIONS=false
LLM_PROVIDER=deterministic
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

Never commit `.env` or credentials.
## Project status

Buildathon prototype. Simulation is the default safety boundary. Razorpay Test Mode execution is opt-in and credential-gated. No live-money movement is enabled by default.
