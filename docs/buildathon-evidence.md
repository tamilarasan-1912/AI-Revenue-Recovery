# RecoverAI — Buildathon Evidence Pack

## Evaluation protocol

RecoverAI reports money recovered across a batch by comparing the same synthetic cohort under two policies:

- **Baseline:** blind retry strategy.
- **RecoverAI:** risk analysis → diagnosis/strategy → deterministic policy → bounded simulated execution.

The synthetic ground-truth field `is_recoverable` is hidden from the agents and is used only after policy authorization to score simulated recovery outcomes.

## Multi-seed protocol

Use the multi-seed endpoint to avoid presenting a cherry-picked run:

`POST /api/simulation/run-multi-seed?size=10000&seeds=42,123,456,789,2026`

The endpoint returns each run plus:

- mean incremental revenue
- incremental-revenue standard deviation
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
5. **Late success:** a successful payment event reconciles an earlier failure instead of blindly starting recovery.

## Recovery evidence

Never claim real-money recovery from the synthetic benchmark. Label it as **simulated recovery**. Razorpay Test Mode execution is opt-in and live-money movement is disabled by default.

For a strong demo, present:

- cohort size
- total revenue at risk
- baseline recovered revenue
- RecoverAI recovered revenue
- incremental revenue
- improvement percentage
- human-review rate
- unsafe-block rate
- fraud-stop rate
- policy-stop rate
- execution rate

## Five-minute demo sequence

**0:00–0:30 — Problem**

Failed payments create revenue leakage. Blind retries waste attempts and can create customer friction.

**0:30–1:00 — Solution**

RecoverAI detects revenue at risk, diagnoses the failure, proposes a bounded intervention, applies deterministic policy, executes safely, and audits the result.

**1:00–2:00 — Live case**

Create the demo review case → show risk/diagnosis/strategy → show policy decision → approve/reject through Human Review.

**2:00–3:00 — Batch evidence**

Run the 10,000-event benchmark and show Baseline vs RecoverAI recovered revenue and incremental revenue.

**3:00–4:00 — Safety**

Demonstrate fraud STOP, retry-budget STOP, low-confidence HUMAN_REVIEW, and duplicate-execution idempotency.

**4:00–4:40 — Architecture**

Show: webhook → risk → diagnosis → strategy → policy → executor → outcome → audit.

**4:40–5:00 — Close**

Emphasize: AI proposes; deterministic policy authorizes; bounded execution recovers eligible revenue; every decision is measurable and auditable.
