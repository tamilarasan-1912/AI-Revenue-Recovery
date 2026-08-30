import uuid
import random
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ExecutionRecord, PolicyDecisionRecord, RecoveryCase, Payment, AuditLog, PaymentStatus, ActionType, PolicyDecisionEnum, ImportedDatasetRow
from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..engine.executor import executor
from ..engine.policy_engine import policy_engine
from ..ml_model import ml_model
from ..recovery_playbook import build_recovery_plan
from ..config import settings
from ..simulation.database_evaluation import evaluate_database_payments

router = APIRouter(); logger = logging.getLogger(__name__)

DEMO_SCENARIOS = [
    {'amount': 7499.0, 'confidence': 0.94, 'failure_reason': 'Synthetic demo: bank timeout; immediate retry is appropriate', 'action': ActionType.RETRY, 'retry_count': 0, 'expected_recovery_value': 5999.20, 'fraud_signal': False, 'label': 'BANK_TIMEOUT_ALLOW'},
    {'amount': 2899.0, 'confidence': 0.90, 'failure_reason': 'Synthetic demo: insufficient funds; payment link is preferred', 'action': ActionType.PAYMENT_LINK, 'retry_count': 0, 'expected_recovery_value': 2319.20, 'fraud_signal': False, 'label': 'INSUFFICIENT_FUNDS_PAYMENT_LINK'},
    {'amount': 19999.0, 'confidence': 0.97, 'failure_reason': 'Synthetic demo: fraud signal detected; recovery must stop', 'action': ActionType.STOP, 'retry_count': 0, 'expected_recovery_value': 0.0, 'fraud_signal': True, 'label': 'FRAUD_STOP'},
    {'amount': 1499.0, 'confidence': 0.95, 'failure_reason': 'Synthetic demo: retry budget exhausted', 'action': ActionType.RETRY, 'retry_count': 3, 'expected_recovery_value': 1199.20, 'fraud_signal': False, 'label': 'RETRY_EXHAUSTION_STOP'},
    {'amount': 12500.0, 'confidence': 0.42, 'failure_reason': 'Synthetic demo: insufficient evidence for automatic recovery', 'action': ActionType.RETRY, 'retry_count': 0, 'expected_recovery_value': 10000.0, 'fraud_signal': False, 'label': 'LOW_CONFIDENCE_HUMAN_REVIEW'},
]


def _load_execution_case(db: Session, execution_id: str):
    row = db.query(ExecutionRecord).filter(ExecutionRecord.id == execution_id).first()
    if not row: raise HTTPException(status_code=404, detail='Execution item not found')
    policy = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.id == row.policy_decision_id).first()
    case = db.query(RecoveryCase).filter(RecoveryCase.id == (policy.recovery_case_id if policy else '')).first() if policy else None
    payment = db.query(Payment).filter(Payment.id == (case.payment_id if case else '')).first() if case else None
    if not policy or not case or not payment: raise HTTPException(status_code=409, detail='Incomplete recovery case')
    return row, policy, case, payment


def _execute_allowed(db, row, policy, case, payment):
    result = executor.execute(db, {'case_id': case.id, 'payment_id': payment.id, 'amount': payment.amount, 'retry_count': payment.retry_count, 'recommended_action': row.action.value, 'ai_confidence': case.ai_confidence or 0.0, 'is_recoverable': (row.result_details or {}).get('actual_is_recoverable')}, 'allow', row.action.value, row.policy_decision_id)
    # Do not create another audit event when the executor returned an idempotent replay.
    if not result.get('idempotent_replay'):
        db.add(AuditLog(id=f'audit_{uuid.uuid4().hex}', event_id=f'execution_{row.id}', payment_id=payment.id, action=row.action.value, outcome=result['status']))
        db.commit()
    return result


def _active_batch_rows(db):
    latest = db.query(ImportedDatasetRow.batch_id).order_by(ImportedDatasetRow.created_at.desc(), ImportedDatasetRow.row_number.desc()).first()
    if not latest: return []
    return db.query(ImportedDatasetRow).filter(ImportedDatasetRow.batch_id == latest[0]).order_by(ImportedDatasetRow.row_number.asc()).all()


def _dataset_row_for_case(db: Session, low_confidence: bool = False):
    rows = _active_batch_rows(db)
    if not rows:
        raise HTTPException(status_code=409, detail='Upload a CSV dataset in Data & Datasets first. RecoverAI no longer uses pre-installed cases.')
    records = [{'payment_id': r.payment_id, 'amount': r.amount, 'failure_reason': r.failure_reason, 'retry_count': r.retry_count, 'is_recoverable': r.is_recoverable} for r in rows]
    if ml_model.model is None or ml_model.training_rows != len(records):
        ml_model.fit(records)
    predictions = ml_model.predict_many(records)
    scored = list(zip(rows, predictions))
    return min(scored, key=lambda item: item[1]['confidence']) if low_confidence else random.choice(scored)


@router.post('/demo')
def create_dataset_review_case(scenario: str | None = Query(None), db: Session = Depends(get_db)):
    try:
        source, ml_prediction = _dataset_row_for_case(db, low_confidence=(scenario == 'LOW_CONFIDENCE_HUMAN_REVIEW'))
        data = {'payment_id': source.payment_id, 'amount': float(source.amount), 'failure_reason': source.failure_reason, 'retry_count': int(source.retry_count), 'ml_recoverability': ml_prediction['recoverability_probability'], 'ml_confidence': ml_prediction['confidence']}
        risk = analyze_risk(data, use_external=False); strategy = recommend_strategy(data, risk, use_external=False); action = strategy['recommended_action']
        recovery_plan = build_recovery_plan(data, max_retries=settings.MAX_RETRIES, retry_delays_hours=settings.retry_delay_hours(), rescue_window_days=settings.RESCUE_WINDOW_DAYS)
        if action == ActionType.RETRY.value and not recovery_plan['retryable']:
            action = recovery_plan['recommended_action']
        policy_result = policy_engine.evaluate({'case_id': source.id, 'payment_id': source.payment_id, 'amount': data['amount'], 'recommended_action': action, 'ai_confidence': strategy['confidence'], 'retry_count': data['retry_count'], 'expected_recovery_value': strategy.get('expected_recovery_value', 0.0), 'fraud_signal': risk.get('fraud_signal', False), 'recovery_plan': recovery_plan})
        decision_enum = PolicyDecisionEnum(policy_result['decision']); token = uuid.uuid4().hex[:12]; payment_id = f'dataset_payment_{token}'; case_id = f'dataset_case_{token}'; policy_id = f'dataset_policy_{token}'; execution_id = f'dataset_execution_{token}'
        payment = Payment(id=payment_id, amount=data['amount'], status=PaymentStatus.FAILED, payment_method='uploaded_csv', failure_reason=data['failure_reason'], retry_count=data['retry_count']); db.add(payment); db.flush()
        case = RecoveryCase(id=case_id, payment_id=payment_id, revenue_at_risk=data['amount'], recommended_action=ActionType(action), ai_confidence=strategy['confidence']); db.add(case); db.flush()
        policy = PolicyDecisionRecord(id=policy_id, recovery_case_id=case_id, decision=decision_enum, policy_version=policy_result['policy_version'], rules_triggered=policy_result['rules_triggered']); db.add(policy); db.flush()
        status = 'PENDING_HUMAN_REVIEW' if decision_enum is PolicyDecisionEnum.HUMAN_REVIEW else ('STOPPED' if decision_enum is PolicyDecisionEnum.STOP else ('BLOCKED' if decision_enum is PolicyDecisionEnum.BLOCK else 'PENDING'))
        attempt = data['retry_count'] if action == 'RETRY' else 0
        execution = ExecutionRecord(id=execution_id, policy_decision_id=policy_id, action=ActionType(action), status=status, idempotency_key=f'recover:{case_id}:{action}:{attempt}', result_details={'dataset_row_id': source.id, 'source_batch': source.batch_id, 'actual_is_recoverable': bool(source.is_recoverable), 'ml_prediction': ml_prediction, 'risk_score': risk.get('risk_score'), 'failure_class': risk.get('failure_class'), 'policy_decision': decision_enum.value, 'recovery_plan': recovery_plan}); db.add(execution); db.flush()
        db.add(AuditLog(id=f'audit_{uuid.uuid4().hex}', event_id=f'dataset_created_{execution_id}', payment_id=payment_id, action=action, outcome=status)); db.commit()
        return {'status': status, 'payment_id': payment_id, 'case_id': case_id, 'execution_id': execution_id, 'amount': data['amount'], 'failure_reason': data['failure_reason'], 'recommended_action': action, 'ai_confidence': strategy['confidence'], 'ml_recoverability': ml_prediction['recoverability_probability'], 'ml_confidence': ml_prediction['confidence'], 'scenario': 'UPLOADED_DATASET', 'policy_decision': decision_enum.value, 'policy_rules': policy_result['rules_triggered'], 'policy_version': policy_result['policy_version'], 'requires_human_review': decision_enum is PolicyDecisionEnum.HUMAN_REVIEW, 'can_execute': decision_enum is PolicyDecisionEnum.ALLOW, 'dataset_row_id': source.id, 'source_batch': source.batch_id, 'recovery_plan': recovery_plan}
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); logger.exception('Failed to create dataset recovery case'); raise HTTPException(status_code=500, detail=f'Could not create dataset recovery case: {exc.__class__.__name__}') from exc


def _materialize_active_batch_reviews(db: Session):
    """Synchronize the active cohort's HUMAN_REVIEW decisions into the actionable queue.

    The synchronization is per dataset row, not an all-or-nothing batch check. This is
    important after a reviewer approves/rejects some rows or after an earlier materializer
    run was interrupted: missing rows are created while existing rows are preserved.
    """
    rows = _active_batch_rows(db)
    if not rows:
        return 0
    batch_id = rows[0].batch_id
    evaluation = evaluate_database_payments(db, limit=min(len(rows), 1000), batch_id=batch_id)
    review_records = [r for r in evaluation.get('records', []) if r.get('policy_decision') == PolicyDecisionEnum.HUMAN_REVIEW.value]
    if not review_records:
        return 0

    existing_keys = {
        e.idempotency_key for e in db.query(ExecutionRecord).filter(ExecutionRecord.idempotency_key.like(f'review:{batch_id}:%')).all()
    }
    created = 0
    for record in review_records:
        action_value = record.get('recommended_action') or ActionType.HUMAN_ESCALATION.value
        try:
            action = ActionType(action_value)
        except ValueError:
            action = ActionType.HUMAN_ESCALATION
        idempotency_key = f'review:{batch_id}:{record.get("row_id")}:{action.value}'
        if idempotency_key in existing_keys:
            continue

        token = uuid.uuid4().hex[:12]
        payment_id = f'review_payment_{token}'
        case_id = f'review_case_{token}'
        policy_id = f'review_policy_{token}'
        execution_id = f'review_execution_{token}'
        payment = Payment(id=payment_id, amount=float(record['amount']), status=PaymentStatus.FAILED, payment_method='uploaded_csv_review', failure_reason=record.get('failure_reason'), retry_count=int(record.get('retry_count', 0)))
        case = RecoveryCase(id=case_id, payment_id=payment_id, revenue_at_risk=float(record['amount']), recommended_action=action, ai_confidence=float(record.get('ai_confidence', 0.0)))
        policy = PolicyDecisionRecord(id=policy_id, recovery_case_id=case_id, decision=PolicyDecisionEnum.HUMAN_REVIEW, policy_version='v1.4-recovery-playbook', rules_triggered=record.get('rules_triggered', []))
        execution = ExecutionRecord(
            id=execution_id,
            policy_decision_id=policy_id,
            action=action,
            status='PENDING_HUMAN_REVIEW',
            idempotency_key=idempotency_key,
            result_details={
                'dataset_row_id': record.get('row_id'),
                'source_batch': batch_id,
                'actual_is_recoverable': bool(record.get('actual_is_recoverable')),
                'ml_prediction': {'recoverability_probability': record.get('ml_recoverability'), 'confidence': record.get('ml_confidence'), 'expected_recovery_amount': record.get('expected_recovery_amount'), 'expected_recovery_rate': record.get('expected_recovery_rate')},
                'risk_score': record.get('risk_score'),
                'failure_class': record.get('failure_class'),
                'policy_decision': PolicyDecisionEnum.HUMAN_REVIEW.value,
                'recovery_plan': record.get('recovery_plan'),
                'materialized_from_active_cohort': True,
            },
        )
        db.add_all([payment, case, policy, execution])
        db.add(AuditLog(id=f'audit_{uuid.uuid4().hex}', event_id=f'review_created_{execution_id}', payment_id=payment_id, action=action.value, outcome='PENDING_HUMAN_REVIEW'))
        existing_keys.add(idempotency_key)
        created += 1

    if created:
        db.commit()
    return created


@router.get('/pending')
def pending_reviews(db: Session = Depends(get_db)):
    try:
        _materialize_active_batch_reviews(db)
    except Exception as exc:
        db.rollback()
        logger.exception('Could not synchronize active cohort human-review cases: %s', exc)

    active_rows = _active_batch_rows(db)
    active_batch = active_rows[0].batch_id if active_rows else None
    query = db.query(ExecutionRecord).filter(ExecutionRecord.status == 'PENDING_HUMAN_REVIEW')
    all_pending = query.order_by(ExecutionRecord.created_at.asc()).all()

    # The queue must reflect the same active cohort as the dashboard/audit log.  Older
    # versions filtered exclusively on the synthetic `review:<batch>:...` idempotency
    # prefix, which hid legitimate PENDING_HUMAN_REVIEW records created by /review/demo
    # (their idempotency key is `recover:...`).  Keep active-batch materialized cases and
    # dataset cases from the same cohort, while excluding unrelated historical records.
    if active_batch:
        rows = [
            row for row in all_pending
            if (row.idempotency_key or '').startswith(f'review:{active_batch}:')
            or (row.result_details or {}).get('source_batch') == active_batch
        ]
    else:
        rows = []

    result = []
    for row in rows:
        try:
            policy = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.id == row.policy_decision_id).first()
            case = db.query(RecoveryCase).filter(RecoveryCase.id == (policy.recovery_case_id if policy else '')).first() if policy else None
            payment = db.query(Payment).filter(Payment.id == (case.payment_id if case else '')).first() if case else None
            if not policy or not case or not payment:
                continue
            result.append({'execution_id': row.id, 'case_id': case.id, 'payment_id': payment.id, 'amount': payment.amount, 'failure_reason': payment.failure_reason, 'recommended_action': row.action.value if row.action else None, 'policy_rules': policy.rules_triggered or [], 'ai_confidence': case.ai_confidence, 'created_at': row.created_at, 'ml_prediction': (row.result_details or {}).get('ml_prediction'), 'recovery_plan': (row.result_details or {}).get('recovery_plan')})
        except Exception:
            logger.exception('Skipping malformed review row: %s', row.id)
    return result


@router.post('/{execution_id}/execute')
def execute_allowed_case(execution_id: str, db: Session = Depends(get_db)):
    row, policy, case, payment = _load_execution_case(db, execution_id)
    if policy.decision.value != 'allow':
        raise HTTPException(status_code=409, detail=f'Policy decision is {policy.decision.value}; direct execution is not allowed')
    if row.status != 'PENDING':
        raise HTTPException(status_code=409, detail=f'Execution is already {row.status}')
    result = _execute_allowed(db, row, policy, case, payment)
    return {'status': result['status'], 'execution_id': row.id, 'result_details': result.get('result_details', {})}


@router.post('/{execution_id}/decision')
def decide_review(execution_id: str, approved: bool, reviewer: str = 'merchant_reviewer', db: Session = Depends(get_db)):
    row, policy, case, payment = _load_execution_case(db, execution_id)
    if row.status != 'PENDING_HUMAN_REVIEW':
        raise HTTPException(status_code=409, detail=f'Review item is no longer pending: {row.status}')
    row.reviewed_by = reviewer
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_decision = 'APPROVED' if approved else 'REJECTED'
    if not approved:
        row.status = 'REJECTED_BY_HUMAN'
        row.result_details = {**(row.result_details or {}), 'reason': 'Merchant rejected recovery action'}
        db.add(AuditLog(id=f'audit_{uuid.uuid4().hex}', event_id=f'review_{row.id}', payment_id=payment.id, action=row.action.value, outcome='REJECTED_BY_HUMAN'))
        db.commit()
        return {'status': row.status, 'execution_id': row.id, 'review_decision': row.review_decision}
    result = _execute_allowed(db, row, policy, case, payment)
    return {'status': result['status'], 'execution_id': row.id, 'review_decision': row.review_decision, 'result_details': result.get('result_details', {})}