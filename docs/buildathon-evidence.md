# RecoverAI — Buildathon Evidence Pack

## Track alignment

Razorpay's current Track 03 bar is explicit: show measured money recovered across a batch, compliant escalation, stopping rules and an audit trail. RecoverAI treats those as the acceptance criteria for the demo rather than dashboard decoration.

## Evaluation protocol

RecoverAI reports money recovered across a batch by comparing the same **held-out synthetic evaluation cohort** under two policies:

- **Baseline:** blind retry strategy.
- **RecoverAI:** learned recoverability signal → risk/diagnosis/strategy → deterministic policy → bounded simulated execution.

The synthetic ground-truth field `is_recoverable` is hidden from the agents and is used only after policy authorization to score simulated recovery outcomes.

The ML benchmark uses a separate training cohort for every evaluation seed. The model is never fitted on the transactions whose recovery revenue is reported. This prevents in-sample leakage and makes the reported recovery lift a held-out evaluation rather than a training-set score.

## Multi-seed protocol

Use the multi-seed endpoint to avoid presenting a cherry-picked run:

`POST /api/simulation/run-multi-seed?dataset_size=10000&seeds=42,123,456,789,2026`

The endpoint returns each run plus:

- mean incremental revenue
- incremental-revenue population standard deviation
- mean improvement vs baseline
- improvement standard deviation
- mean RecoverAI revenue-recovery rate
- mean baseline revenue-recovery rate
- mean human-review rate
- mean unsafe-block rate

For the final presentation, report the aggregate mean and standard deviation and keep the individual seed results available as evidence.

## Safety scenarios

The demo should explicitly show:

1. **Fraud:** policy stops the recovery action.
2. **Retry exhaustion:** policy stops another retry after the retry budget is exhausted.
3. **Low confidence:** policy routes the case to human review.
4. **Duplicate logical execution:** idempotency prevents a second logical execution.
5. **Duplicate webhook:** the same Razorpay event ID is ignored.
6. **Late success:** a successful payment event reconciles an earlier failure and cancels stale pending recovery execution.
7. **Stale webhook:** events outside the configured freshness window are rejected.

## Recovery evidence

Never claim real-money recovery from the synthetic benchmark. Label it as **simulated recovery**. Razorpay Test Mode execution is opt-in and live-money movement is disabled by default.

For a strong demo, present:

- evaluation cohort size
- independent training cohort size
- total revenue at risk
- baseline recovered revenue
- RecoverAI recovered revenue
- incremental revenue
- improvement percentage
- human-review rate
- unsafe-block rate
- fraud-stop rate
- policy-stop rate
- intervention execution rate
- model version and holdout protocol

## Five-minute demo sequence

**0:00–0:30 — Problem**

Failed payments create revenue leakage. Blind retries waste attempts and can create customer friction.

**0:30–1:00 — Solution**

RecoverAI detects revenue at risk, diagnoses the failure, proposes a bounded intervention, applies deterministic policy, executes safely, and audits the result.

**1:00–2:00 — Live case**

Create a dataset-backed recovery case → show ML/risk/diagnosis/strategy → show policy decision → approve/reject through Human Review.

**2:00–3:00 — Batch evidence**

Run the 10,000-event held-out benchmark and show Baseline vs RecoverAI recovered revenue and incremental revenue. Also show the independent training-cohort size.

**3:00–4:00 — Safety**

Demonstrate fraud STOP, retry-budget STOP, low-confidence HUMAN_REVIEW, duplicate-execution idempotency, duplicate webhook handling and late-success cancellation.

**4:00–4:40 — Architecture**

Show: webhook → feature/ML score → risk/diagnosis → strategy → deterministic policy → bounded executor → outcome → audit.

**4:40–5:00 — Close**

Emphasize: AI proposes; deterministic policy authorizes; bounded execution recovers eligible revenue; every decision is measurable and auditable.
