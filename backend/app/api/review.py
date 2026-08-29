import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ExecutionRecord, PolicyDecisionRecord, RecoveryCase, Payment, AuditLog, PaymentStatus, ActionType
from ..engine.executor import executor
from ..engine.policy_engine import policy_engine

router = APIRouter()


DEMO_SCENARIOS = [
    {
        'amount': 7499.0,
        'confidence': 0.94,
        'failure_reason': 'Synthetic demo: bank timeout; immediate retry is appropriate',
        'action': ActionType.RETRY,
        'retry_count': 0,
        'expected_recovery_value': 5999.20,
        'fraud_signal': False,
        'label': 'BANK_TIMEOUT_ALLOW',
    },
    {
        'amount': 2899.0,
        'confidence': 0.90,
        'failure_reason': 'Synthetic demo: insufficient funds; payment link is preferred',
        'action': ActionType.PAYMENT_LINK,
        'retry_count': 0,
        'expected_recovery_value': 2319.20,
        'fraud_signal': False,
        'label': 'INSUFFICIENT_FUNDS_PAYMENT_LINK',
    },
    {
        'amount': 19999.0,
        'confidence': 0.97,
        'failure_reason': 'Synthetic demo: fraud signal detected; recovery must stop',
        'action': ActionType.STOP,
        'retry_count': 0,
        'expected_recovery_value': 0.0,
        'fraud_signal': True,
        'label': 'FRAUD_STOP',
    },
    {
        'amount': 1499.0,
        'confidence': 0.95,
        'failure_reason': 'Synthetic demo: retry budget exhausted',
        'action': ActionType.RETRY,
        'retry_count': 3,
        'expected_recovery_value': 1199.20,
        'fraud_signal': False,
        'label': 'RETRY_EXHAUSTION_STOP',
    },
    {
        'amount': 12500.0,
        'confidence': 0.42,
        'failure_reason': 'Synthetic demo: insufficient evidence for automatic recovery',
        'action': ActionType.RETRY,
        'retry_count': 0,
        'expected_recovery_value': 10000.0,
        'fraud_signal': False,
        'label': 'LOW_CONFIDENCE_HUMAN_REVIEW',
    },
]


def _load_execution_case(db: Session, execution_id: str):
    row = db.query(ExecutionRecord).filter(ExecutionRecord.id == execution_id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Execution item not found')
    policy = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.id == row.policy_decision_id).first()
    case = db.query(RecoveryCase).filter(RecoveryCase.id == (policy.recovery_case_id if policy else '')).first() if policy else None
    payment = db.query(Payment).filter(Payment.id == (case.payment_id if case else '')).first() if case else None
    if not policy or not case or not payment:
        raise HTTPException(status_code=409, detail='Incomplete recovery case')
    return row, policy, case, payment


def _execute_allowed(db: Session, row: ExecutionRecord, policy: PolicyDecisionRecord, case: RecoveryCase, payment: Payment):
    result = executor.execute(
        db,
        {
            'case_id': case.id,
            'payment_id': payment.id,
            'amount': payment.amount,
            'retry_count': payment.retry_count,
            'recommended_action': row.action.value,
            'ai_confidence': case.ai_confidence or 0.0,
        },
        'allow',
        row.action.value,
        row.policy_decision_id,
    )
    db.add(AuditLog(
        id=f'audit_{uuid.uuid4().hex}',
        event_id=f'execution_{row.id}',
        payment_id=payment.id,
        action=row.action.value,
        outcome=result['status'],
    ))
    db.commit()
    return result


@router.post('/demo')
def create_demo_review_case(db: Session = Depends(get_db)):
    """Create a deterministic governance scenario whose UI mirrors policy output.

    No payment provider is called. The scenario is evaluated by the same
    deterministic PolicyEngine used by real webhook decisions.
    """
    token = uuid.uuid4().hex[:12]
    scenario = DEMO_SCENARIOS[int(token[-4:], 16) % len(DEMO_SCENARIOS)]
    payment_id = f'demo_payment_{token}'
    case_id = f'demo_case_{token}'
    policy_id = f'demo_policy_{token}'
    execution_id = f'demo_execution_{token}'
    amount = scenario['amount']
    confidence = scenario['confidence']
    action = scenario['action'].value

    payment = Payment(
        id=payment_id,
        amount=amount,
        status=PaymentStatus.FAILED,
        payment_method='card',
        failure_reason=scenario['failure_reason'],
        retry_count=scenario['retry_count'],
    )
    case = RecoveryCase(
        id=case_id,
        payment_id=payment_id,
        revenue_at_risk=amount,
        recommended_action=scenario['action'],
        ai_confidence=confidence,
    )
    policy_result = policy_engine.evaluate({
        'case_id': case_id,
        'payment_id': payment_id,
        'amount': amount,
        'recommended_action': action,
        'ai_confidence': confidence,
        'retry_count': scenario['retry_count'],
        'expected_recovery_value': scenario['expected_recovery_value'],
        'fraud_signal': scenario['fraud_signal'],
    })
    policy = PolicyDecisionRecord(
        id=policy_id,
        recovery_case_id=case_id,
        decision=policy_result['decision'],
        policy_version=policy_result['policy_version'],
        rules_triggered=policy_result['rules_triggered'],
    )

    db.add_all([payment, case, policy])
    db.flush()

    decision = policy_result['decision']
    if decision == 'human_review':
        execution_status = 'PENDING_HUMAN_REVIEW'
    elif decision in {'stop', 'block'}:
        execution_status = 'STOPPED' if decision == 'stop' else 'BLOCKED'
    else:
        execution_status = 'PENDING'

    execution = ExecutionRecord(
        id=execution_id,
        policy_decision_id=policy_id,
        action=scenario['action'],
        status=execution_status,
        idempotency_key=f'demo_review_{token}',
        result_details={
            'demo': True,
            'scenario': scenario['label'],
            'ai_confidence': confidence,
            'policy_decision': decision,
            'policy_rules': policy_result['rules_triggered'],
            'note': 'Synthetic case; no real-money movement',
        },
    )
    db.add(execution)
    db.add(AuditLog(
        id=f'audit_{uuid.uuid4().hex}',
        event_id=f'demo_created_{execution_id}',
        payment_id=payment_id,
        action=action,
        outcome=execution_status,
    ))
    db.commit()

    return {
        'status': execution_status,
        'payment_id': payment_id,
        'case_id': case_id,
        'execution_id': execution_id,
        'amount': amount,
        'failure_reason': scenario['failure_reason'],
        'recommended_action': action,
        'ai_confidence': confidence,
        'scenario': scenario['label'],
        'policy_decision': decision,
        'policy_rules': policy_result['rules_triggered'],
        'policy_version': policy_result['policy_version'],
        'requires_human_review': decision == 'human_review',
        'can_execute': decision == 'allow',
        'demo': True,
    }


@router.get('/pending')
def pending_reviews(db: Session = Depends(get_db)):
    rows = db.query(ExecutionRecord).filter(ExecutionRecord.status == 'PENDING_HUMAN_REVIEW').order_by(ExecutionRecord.created_at.asc()).all()
    result = []
    for row in rows:
        policy = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.id == row.policy_decision_id).first()
        case = db.query(RecoveryCase).filter(RecoveryCase.id == (policy.recovery_case_id if policy else '')).first() if policy else None
        payment = db.query(Payment).filter(Payment.id == (case.payment_id if case else '')).first() if case else None
        result.append({
            'execution_id': row.id,
            'case_id': case.id if case else None,
            'payment_id': payment.id if payment else None,
            'amount': payment.amount if payment else None,
            'failure_reason': payment.failure_reason if payment else None,
            'recommended_action': row.action.value if row.action else None,
            'policy_decision_id': row.policy_decision_id,
            'policy_rules': policy.rules_triggered if policy else [],
            'ai_confidence': case.ai_confidence if case else None,
            'created_at': row.created_at,
        })
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
        raise HTTPException(status_code=409, detail='Review item is no longer pending')

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
