# RecoverAI

**Evidence-first AI Revenue Recovery Control Center for Razorpay merchants.**

RecoverAI turns a failed payment into a bounded recovery case:

**detect revenue at risk → learn recoverability → diagnose the failure → recommend an intervention → apply deterministic policy → execute safely → measure the outcome → audit every decision.**

## Why this project is different

Razorpay's Track 03 asks builders to go beyond identifying the problem: show measured money recovered across a batch, compliant escalation, stopping rules and an audit trail. RecoverAI is engineered around those proof points.

The project combines, in one workflow:

- Razorpay-style webhook signature validation, freshness checks and duplicate-event protection.
- Late-success reconciliation that cancels stale pending recovery actions.
- Behaviour-based ML recoverability scoring and expected-recovery estimation.
- AI-assisted risk/diagnosis/strategy with deterministic authorization outside the model.
- Canonical idempotency keys at the executor boundary.
- Human review for low-confidence decisions.
- Optional Razorpay **Test Mode** execution, explicitly disabled by default.
- A reproducible held-out batch simulator with single-seed and five-seed evidence runs.
- CSV evaluation and explicit dataset import boundaries.
- Failure injection for retry-exhaustion and duplicate-execution resilience.
- An inspectable policy console so a judge can see exactly why an action was allowed, stopped, blocked or escalated.

## Architecture

```text
Razorpay Test Mode webhook
          ↓
 Signature + freshness validation
          ↓
 Duplicate event protection
          ↓
 Feature extraction → ML recoverability score
          ↓
 Risk / Diagnosis / Strategy agents
          ↓
 Deterministic Policy Engine
       ↙       ↓        ↘
   ALLOW     HUMAN     STOP/BLOCK
      ↓      REVIEW        ↓
 Bounded executor       Audit log
      ↓
 Simulation / Razorpay Test Mode adapter
      ↓
 Outcome + recovery metrics
```

The model has **no execution authority**. The executor accepts only policy-authorized actions, applies idempotency, and rejects live Razorpay credentials at the buildathon safety boundary.

## AI and ML layer

- RandomForest-based recoverability classifier trained on payment behaviour and failure context.
- RandomForest expected-recovery estimator when recovered amounts/rates are available; otherwise a clearly documented proxy is used.
- Behaviour features include payment method, decline/error context, retry pressure, customer history, timing, outstanding amount and reminder response signals when present.
- Optional OpenAI-compatible structured model endpoint for risk/strategy generation.
- Deterministic fallback keeps the prototype runnable without an external API key.
- Structured outputs are validated before policy evaluation.
- The benchmark model is trained on an **independent synthetic cohort** and scored on a separate held-out cohort, eliminating in-sample recovery-lift leakage.

## Policy and safety layer

- Fraud signals force `STOP`.
- Retry budget is bounded by `MAX_RETRIES`.
- Low-confidence recommendations route to `HUMAN_REVIEW`.
- `WAIT` is never treated as an immediate money action.
- Low expected recovery value can stop an intervention.
- Every execution gets a deterministic idempotency key.
- Duplicate webhook delivery is detected using Razorpay's event identifier.
- Stale webhook payloads are rejected using the configured freshness window.
- Late `payment.captured` / successful events update the payment and cancel stale pending recovery execution.
- Production does not silently fall back to a second database; SQLite fallback is opt-in for isolated local demos only.

## Batch evidence

The Simulation Lab evaluates a synthetic failed-payment cohort against a blind-retry baseline. Every benchmark run trains on a separate synthetic cohort and reports outcomes only on the held-out evaluation cohort. The final evidence run uses **5 independent seeds × 10,000 evaluation events**, with mean and population standard deviation.

The runtime result reports:

- revenue at risk
- recoverable revenue
- baseline recovered revenue
- RecoverAI recovered revenue
- recovery rate
- incremental revenue
- improvement vs baseline
- human-review rate
- unsafe actions blocked
- policy stop rate
- fraud stop rate
- intervention/action distribution
- model version and training/evaluation sizes

The benchmark is synthetic evidence, not a claim of live Razorpay revenue recovery. That boundary is intentional and documented.

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

## Production deployment

The repository includes a Render Blueprint (`render.yaml`) that provisions the backend, managed Postgres database, and a static frontend. The backend exposes `/api/system/health` as the HTTP readiness check, and the static frontend receives the backend's public URL at build time. This provides a deployment path independent of Vercel's build limits. Vercel remains supported when its deployment quota is available.

Set these production secrets/environment variables in the deployment platform:

```text
DATABASE_URL=<managed PostgreSQL connection string>
RAZORPAY_KEY_ID=<rzp_test_* for demo execution>
RAZORPAY_KEY_SECRET=<test secret>
RAZORPAY_WEBHOOK_SECRET=<webhook secret>
ENABLE_RAZORPAY_TEST_ACTIONS=false
ALLOW_SQLITE_FALLBACK=false
REQUIRE_WEBHOOK_SIGNATURE=true
WEBHOOK_MAX_AGE_SECONDS=300
LLM_PROVIDER=deterministic
```

Never commit `.env` or credentials.

## Buildathon positioning

RecoverAI targets Track 03 — **AI Revenue Recovery**. The strongest evidence is not a screenshot: it is the reproducible batch result, held-out ML protocol, bounded policy decisions, failure handling and audit trail.

## Project status

Buildathon prototype with production-oriented safety boundaries. Simulation is the default execution boundary. Razorpay Test Mode execution is opt-in and live-money movement is disabled by default.
