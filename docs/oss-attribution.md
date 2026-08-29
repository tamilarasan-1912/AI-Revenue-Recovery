# Open-source engineering references

RecoverAI is an independent implementation. The following public repositories were studied for engineering patterns; their code is not copied into this repository unless explicitly noted.

## Etherlabs Payment Recovery Engine

Repository: https://github.com/Etherlabs-dev/payment_recovery_engine

Studied patterns: deterministic failure classification, bounded retry schedules, idempotent state transitions, PostgreSQL persistence, retry leases, duplicate-event suppression, Docker and test structure.

License: MIT. If code is ever reused directly, retain the original copyright/license notice as required by that license.

## Jaktra

Repository: https://github.com/Jaktra-org/Jaktra

Studied patterns: receivables workflow, risk scoring, payment-link recovery, communication escalation, DLQ concepts, agent controls, and separation of an AI service from the transactional backend.

## Revenue Resilience AI

Repository: https://github.com/srikrishna0603/razorpay-buildathon

Studied patterns: strict separation between probabilistic diagnosis and deterministic policy, economic thresholds, idempotency, failure injection, held-out synthetic evaluation, and auditability.

This repository was treated as an architecture reference rather than a submission base because it is itself a Razorpay Buildathon 2026 project.

## RecoverAI design boundary

RecoverAI's implementation and product decisions remain its own. AI proposes diagnoses/strategies; the deterministic Policy Engine controls financial actions; the executor is restricted to simulation or explicitly enabled Razorpay Test Mode; and every recovery event is auditable.
