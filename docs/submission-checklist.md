# RecoverAI — Razorpay Buildathon Submission Checklist

This checklist is intentionally conservative: an item is only marked ready when it has been verified rather than assumed.

## Track 03 — AI Revenue Recovery

Razorpay's bar is measured money recovered across a batch, compliant escalation, stopping rules, and an audit trail.

### Product

- [x] Revenue-at-risk detection
- [x] Failure diagnosis / strategy selection
- [x] Deterministic policy gate
- [x] Bounded recovery actions
- [x] Human-review path
- [x] Audit log
- [x] Idempotency protection
- [x] Late-success reconciliation
- [x] Synthetic batch benchmark
- [x] Multi-seed evaluation endpoint
- [x] CSV upload evaluation
- [x] Explicit CSV → demo PostgreSQL import
- [x] Exact imported-batch database evaluation

### Evidence

- [x] Baseline vs RecoverAI comparison
- [x] Incremental revenue metric
- [x] Recovery-rate metrics
- [x] Human-review rate
- [x] Unsafe-block metric
- [x] Fraud-stop scenario
- [x] Retry-budget-stop scenario
- [x] Low-confidence human-review scenario
- [x] Duplicate-execution idempotency scenario
- [x] Late-success scenario
- [ ] Run final 10,000-event multi-seed benchmark on the deployed environment
- [ ] Record final aggregate mean/stddev numbers for the pitch

### Deployment verification

- [x] Backend test suite exists
- [x] Frontend production build exists
- [x] GitHub Actions CI workflow added for backend tests + frontend build
- [ ] Confirm latest CI run is green
- [ ] Confirm deployed frontend → deployed backend API connectivity
- [ ] Confirm PostgreSQL import/evaluation on deployed backend
- [ ] Confirm Human Review approval/rejection on deployed environment
- [ ] Confirm Audit Log records the demo flow

### Submission assets

- [x] Public GitHub repository
- [x] Architecture documentation
- [x] Buildathon evidence pack
- [x] Five-minute demo sequence
- [ ] Final 5-minute pitch recording
- [ ] Final architecture screenshot/diagram
- [ ] Final deployed demo URL
- [ ] Final repository URL checked

## Stop condition before pitch

Do **not** call RecoverAI submission-ready until every unchecked deployment/evidence item above has been verified. The final pitch should use the verified aggregate metrics and the deployed application, not screenshots or numbers produced from an unverified local-only run.
