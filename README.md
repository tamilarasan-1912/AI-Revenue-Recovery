# RecoverAI — AI Revenue Recovery Control Center

**RecoverAI** is an evidence-first revenue recovery platform for payment failures. It turns a failed transaction into a bounded recovery case:

> **Detect revenue at risk → score recoverability → diagnose the failure → recommend a recovery strategy → enforce deterministic policy → execute safely → reconcile the outcome → measure recovered revenue → audit the decision.**

Built for the Razorpay AI Buildathon **Track 03 — AI Revenue Recovery**, the project focuses on the part that matters after a payment fails: recovering legitimate revenue without blindly retrying, over-contacting customers, or giving an AI model direct execution authority.

[![Backend Tests](https://github.com/tamilarasan-1912/AI-Revenue-Recovery/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/tamilarasan-1912/AI-Revenue-Recovery/actions/workflows/backend-tests.yml)
[![CI](https://github.com/tamilarasan-1912/AI-Revenue-Recovery/actions/workflows/ci.yml/badge.svg)](https://github.com/tamilarasan-1912/AI-Revenue-Recovery/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## Product in one sentence

RecoverAI combines **payment-event handling, behavioural ML, AI-assisted diagnosis/strategy, deterministic safety policy, bounded execution, simulation, reconciliation, analytics, and auditability** into one recovery workflow.

---

## Architecture

```mermaid
flowchart LR
    U[Merchant / Operations User] --> UI[React + Vite Control Center]
    UI --> API[FastAPI API]

    WH[Razorpay-style Webhook] --> WV[Signature + Freshness Validation]
    WV --> DD[Duplicate Event Guard]
    DD --> PE[Payment / Recovery Case]

    API --> PE
    PE --> FE[Feature Extraction]
    FE --> ML[Recovery ML Model]
    PE --> DG[Diagnosis Agent]
    ML --> RA[Risk Agent]
    DG --> SA[Strategy Agent]
    RA --> SA

    SA --> PG[Deterministic Policy Engine]
    PG -->|ALLOW| EX[Bounded Executor]
    PG -->|HUMAN_REVIEW| HR[Human Review Queue]
    PG -->|STOP / BLOCK| ST[Stop / Block]

    EX --> SIM[Simulation Adapter]
    EX --> RZ[Razorpay Test Mode Adapter]
    SIM --> OR[Outcome Reconciliation]
    RZ --> OR
    OR --> DB[(PostgreSQL / SQLite local demo)]

    DB --> AN[Analytics + Benchmark]
    DB --> AU[Audit Log]
    AN --> UI
    AU --> UI
```

### Architectural principle

**The model cannot execute a payment action.** The ML/AI layer recommends; the deterministic policy layer authorizes; the executor applies the approved action with an idempotency key. This separation is deliberate because payment recovery combines optimization with financial and fraud-risk constraints.

The backend is implemented as a FastAPI application with dedicated routers for webhooks, analytics, audit, simulation, review, failure injection, system health, payments, and recovery.

---

## End-to-end recovery flow

```mermaid
flowchart TD
    A[Payment fails] --> B[Receive payment event]
    B --> C{Signature valid<br/>and event fresh?}
    C -->|No| X[Reject + audit]
    C -->|Yes| D{Duplicate event?}
    D -->|Yes| Y[Ignore duplicate + audit]
    D -->|No| E[Create / update recovery case]

    E --> F[Extract payment + behavioural features]
    F --> G[Predict recoverability probability]
    G --> H[Estimate expected recovery amount]

    E --> I[Diagnose failure reason]
    I --> J[Generate bounded recovery strategy]
    H --> K[Combine evidence]
    J --> K

    K --> L{Deterministic policy gate}
    L -->|Fraud / unsafe| M[STOP]
    L -->|Low confidence| N[HUMAN REVIEW]
    L -->|Not economical / not allowed| O[BLOCK]
    L -->|Approved| P[Execute bounded action]

    P --> Q{Execution result}
    Q -->|Success| R[Mark recovered]
    Q -->|Failure| S{Retry budget available?}
    S -->|Yes| T[Schedule next bounded attempt]
    S -->|No| U[Stop recovery]

    R --> V[Reconcile payment state]
    T --> V
    U --> V
    M --> V
    N --> V
    O --> V

    V --> W[Analytics + revenue-at-risk metrics]
    W --> Z[Audit trail]
```
## Core capabilities

### 1. Payment event ingestion

RecoverAI treats webhooks as the system-of-record trigger for recovery state changes.

Supported safety controls include:

- signature validation
- freshness-window checks
- duplicate-event protection
- late-success reconciliation
- stale recovery cancellation

This mirrors the practical requirement in payment systems to process retries and outcomes through reliable event notifications rather than assuming a synchronous payment response tells the entire story.

### 2. Behaviour-based recoverability ML

The repository implements a supervised recovery model using **scikit-learn**:

- `RandomForestClassifier` for recoverability propensity
- `RandomForestRegressor` for expected recovery amount
- `DictVectorizer` for mixed categorical/numeric features
- held-out validation for benchmark metrics
- deterministic model version and training identity

The feature layer can use payment method, decline/error context, retry count, recurrence, authentication requirements, card expiry timing, customer tenure, historical payment success, days past due, payment timing, prior failure/delay counts, outstanding balance, reminder response, and related behavioural signals.

The implementation also keeps the supervised target `is_recoverable` out of the input feature set, preventing direct target leakage.

### 3. Failure diagnosis

The diagnosis layer normalizes failures into bounded classes such as:

- `temporary_bank_degradation`
- `insufficient_funds`
- `authentication_required`
- `payment_method_invalid`
- `fraud_suspected`
- `hard_decline`
- `unknown_payment_failure`

It also produces evidence and a bounded retry-safety signal.

### 4. AI-assisted strategy generation

The architecture supports risk, diagnosis, strategy, and communication agents. An optional OpenAI-compatible provider can enrich recommendations, while deterministic behaviour keeps the prototype runnable without depending on an external LLM.

The important boundary is that generated content remains **structured evidence/recommendation**, not an executable payment instruction.

### 5. Deterministic policy engine

The policy engine is the final safety gate.

Current rules include:

- block actions outside the configured allowed-action set
- stop on fraud signals
- prevent retries when the recovery plan marks them as non-retryable
- stop when no retry window is available
- route explicit escalation to human review
- stop when maximum retries are reached
- route `WAIT` decisions to human review instead of treating them as immediate money movement
- escalate low-confidence recommendations
- stop interventions when expected recovery value is below the configured intervention cost

The model is advisory; the policy engine is the deterministic authorization boundary.

### 6. Safe execution + idempotency

Execution occurs only after policy authorization. The system uses a canonical idempotency boundary to reduce duplicate-action risk.

For payment infrastructure, idempotency is especially important when clients retry requests after timeouts or transient server errors. Razorpay's documentation likewise describes using the same idempotency key for safe retries of eligible operations.

### 7. Human-in-the-loop recovery

Not every payment failure should be auto-executed. RecoverAI can route uncertain or explicitly escalated cases for review so that an operator can inspect:

- payment evidence
- diagnosis
- model confidence
- expected recovery value
- policy rules triggered
- proposed action
- audit history

### 8. Simulation and evidence

The Simulation Lab is designed to answer the buildathon's hardest question:

> **Does the recovery strategy actually recover more money than a baseline?**

The project benchmarks a synthetic failed-payment cohort against a blind-retry baseline and keeps the training cohort separate from the evaluation cohort. The five-seed evaluation protocol uses **5 independent seeds × 10,000 evaluation events** and reports aggregate mean and population standard deviation.

Reported evidence includes:

- revenue at risk
- recoverable revenue
- baseline recovered revenue
- RecoverAI recovered revenue
- recovery rate
- incremental revenue
- improvement versus baseline
- human-review rate
- unsafe actions blocked
- policy-stop and fraud-stop rates
- action distribution
- model version
- training/evaluation sizes

These numbers are explicitly **synthetic benchmark evidence**, not claims about live Razorpay production revenue.

---

## Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Recovery control center UI |
| UI / Styling | Tailwind CSS + Lucide React | Dashboard and interaction layer |
| Charts | Recharts | Recovery analytics and benchmark visualization |
| HTTP client | Axios | Frontend-to-backend API calls |
| Backend | FastAPI + Uvicorn | REST APIs, webhooks, orchestration |
| Validation | Pydantic / pydantic-settings | Typed request/config validation |
| ML | scikit-learn | Recoverability classification + recovery estimation |
| Persistence | SQLAlchemy + PostgreSQL | Recovery state, analytics, audit history |
| Local demo DB | SQLite (opt-in) | Isolated local demonstration |
| Testing | Pytest | Backend correctness and resilience tests |
| Packaging | Docker / Docker Compose | Reproducible local environment |
| Deployment | Render Blueprint / Vercel frontend support | Cloud deployment path |

---

## Repository structure

```text
AI-Revenue-Recovery/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── communication_agent.py
│   │   │   ├── diagnosis_agent.py
│   │   │   ├── llm_provider.py
│   │   │   ├── risk_agent.py
│   │   │   └── strategy_agent.py
│   │   ├── api/
│   │   │   ├── analytics.py
│   │   │   ├── audit.py
│   │   │   ├── failure_injection.py
│   │   │   ├── payments.py
│   │   │   ├── recovery.py
│   │   │   ├── review.py
│   │   │   ├── simulation.py
│   │   │   ├── system.py
│   │   │   └── webhooks.py
│   │   ├── engine/
│   │   │   ├── executor.py
│   │   │   ├── idempotency.py
│   │   │   └── policy_engine.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   └── ml_model.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── .github/
│   └── workflows/
│       ├── backend-tests.yml
│       ├── benchmark.yml
│       └── ci.yml
├── docker-compose.yml
├── render.yaml
├── .env.example
└── README.md
```

| Risk | Control |
|---|---|
| Fraudulent transaction | Immediate policy `STOP` |
| Excessive retries | Maximum retry budget |
| Low-confidence recommendation | `HUMAN_REVIEW` |
| Unsupported action | Policy `BLOCK` |
| Uneconomic intervention | Expected-value threshold |
| Duplicate webhook | Event identity guard |
| Stale webhook | Freshness window |
| Late payment success | Reconciliation + stale-action cancellation |
| Duplicate execution | Canonical idempotency key |
| Live-money accident | Test/simulation boundary |

---

## Benchmark methodology

A strong revenue-recovery system should not evaluate itself on the same records it used for training. RecoverAI therefore separates:

1. **Training cohort** — used to fit the recoverability model.
2. **Held-out evaluation cohort** — never shown during model fitting.
3. **Baseline policy** — blind-retry comparison.
4. **Recovery policy** — ML/AI recommendation followed by deterministic authorization.
5. **Repeated seeds** — used to measure variability instead of presenting a single lucky run.

The ML module calculates held-out classification metrics including accuracy, precision, recall, F1, and ROC-AUC when there are enough examples and both classes are present.

### What the benchmark is intended to prove

- Whether the policy recovers more value than a simple baseline.
- Whether the system avoids unsafe actions.
- Whether human escalation occurs where expected.
- Whether action decisions remain bounded under adverse scenarios.
- Whether duplicate and retry failures preserve execution safety.

### What the benchmark does **not** prove

Synthetic benchmark recovery is **not** evidence of a guaranteed live-business lift. Real deployment would require production data, cohort monitoring, calibration, fraud/risk integration, payment-network constraints, and ongoing model governance.

---

## Failure injection and resilience testing

The project includes dedicated failure-injection endpoints/modules so the team can demonstrate behaviour under conditions such as:

- duplicate execution attempts
- retry exhaustion
- repeated payment failure
- delayed or late-success events
- blocked or stopped policy decisions

This matters because revenue recovery is not just a prediction problem; it is a **distributed systems + risk + optimization** problem. Payment providers also document retry outcomes, retry windows, fraud declines, and maximum retry attempts.

---


## Deployment

The repository includes deployment configuration for:

- **Render**: backend + managed PostgreSQL + static frontend through `render.yaml`
- **Vercel**: supported frontend deployment path
- **Docker**: local and containerized deployment

The production architecture should keep PostgreSQL as the primary database and maintain the same policy, webhook, and execution boundaries used in the local system.

---

## Research references

The design is informed by publicly documented payment-recovery patterns:

- Razorpay — Payment Retries: recurring-payment failures, webhook handling, retry behaviour, and payment-method changes.
- Adyen — Auto Rescue: smart retry timing, retry windows, webhook outcomes, fraud-stop behaviour, maximum retry attempts, and payment-link fallback.
- Adyen — Payment lifecycle: refusal/error handling and retry-aware payment states.
- Stripe Engineering — Smart Retries: ML-based retry-timing optimization using payment and behavioural features.

These references are used for design context; RecoverAI's benchmark values and implementation remain specific to this repository.

---

## Project status

**prototype with production-oriented safety boundaries.**

Simulation is the default execution boundary. Live-money movement is not enabled by default.

---

## License

Licensed under the **Apache License 2.0**. See [LICENSE](LICENSE).

---

## Repository

**GitHub:** https://github.com/tamilarasan-1912/AI-Revenue-Recovery

**Live frontend:** https://frontend-three-dun-22.vercel.app
