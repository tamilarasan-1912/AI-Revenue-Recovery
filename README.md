# RecoverAI

**Evidence-first AI Revenue Recovery Control Center for Razorpay merchants.**

RecoverAI turns a failed payment into a bounded recovery case:

**detect revenue at risk → diagnose the failure → recommend an intervention → apply deterministic policy → execute safely → measure the outcome → audit every decision.**

## Why this project is different

Public Track 03 projects increasingly converge on the same headline idea: an AI agent chooses a retry or customer intervention. RecoverAI deliberately competes on the harder engineering boundary around that idea.

The project combines, in one workflow:

- Razorpay-style webhook signature validation and duplicate-event protection.
- Late-success reconciliation so a later success does not trigger a stale recovery action.
- AI-assisted risk/diagnosis/strategy with deterministic authorization outside the model.
- Canonical idempotency keys at the executor boundary.
- Human review for low-confidence decisions.
- Optional Razorpay **Test Mode** execution, explicitly disabled by default.
- A reproducible batch simulator with single-seed and five-seed evidence runs.
- CSV evaluation and explicit demo-database import boundaries.
- Failure injection for retry-exhaustion and duplicate-execution resilience.
- An inspectable policy console so a judge can see exactly why an action was allowed, stopped, blocked or escalated.

This is a qualified differentiation claim: it describes the combination implemented here and is not a claim that no other repository has any individual feature.

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
   Diagnosis / Strategy
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
- Demo scenarios are evaluated by the same PolicyEngine as webhook-driven cases; the UI does not invent confidence or policy outcomes.

## Batch evidence

The Simulation Lab evaluates a synthetic failed-payment cohort against a blind-retry baseline. A single-seed run is reproducible from its seed; the final evidence card runs **5 independent seeds × 10,000 events** and reports mean and population standard deviation.

The runtime result reports:

- revenue at risk
- recovered revenue
- recovery rate
- incremental revenue
- improvement vs blind retry
- human-review rate
- unsafe actions blocked
- policy stop rate
- fraud stop rate
- intervention/action distribution

**The final evidence UI starts blank until the benchmark is actually run. It does not display memorized benchmark numbers.**

The benchmark is synthetic evidence, not a claim of live Razorpay revenue recovery. That boundary is intentional and documented.

## Demo scenarios

1. Temporary bank timeout → bounded retry or payment-link recovery.
2. Insufficient funds → payment-link intervention.
3. Fraud suspected → deterministic STOP.
4. Retry budget exhausted → deterministic STOP.
5. Low AI confidence → HUMAN_REVIEW.
6. Duplicate Razorpay webhook → ignored by event ID.
7. Late successful payment after a failure → payment state reconciled.
8. Duplicate logical execution → same idempotency key, no second execution.
9. Failure injection → proves retry exhaustion and idempotency protection.

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

Frontend build:

```bash
cd frontend
npm install
npm run build
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

## Buildathon positioning

Razorpay's official Track 03 bar is explicit: do not stop at identifying the problem; show measured money recovered across a batch, compliant escalation, stopping rules and an audit trail. RecoverAI is designed around those four proof points rather than treating the dashboard as the product. citeturn1search0

## Project status

Buildathon prototype. Simulation is the default safety boundary. Razorpay Test Mode execution is opt-in and credential-gated. No live-money movement is enabled by default.
