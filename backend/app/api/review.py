import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ExecutionRecord, PolicyDecisionRecord, RecoveryCase, Payment, AuditLog, PaymentStatus, ActionType, PolicyDecisionEnum
from ..engine.executor import executor

router = APIRouter()


DEMO_SCENARIOS = [
    {
        'amount': 12500.0,
        'confidence': 0.42,
        'failure_reason': 'Synthetic demo: insufficient evidence for automatic recovery',
        'action': ActionType.RETRY,
        'label': 'LOW_CONFIDENCE_RETRY',
    },
    {
        'amount': 7499.0,
        'confidence': 0.48,
        'failure_reason': 'Synthetic demo: bank timeout with limited evidence',
        'action': ActionType.RETRY,
        'label': 'BANK_TIMEOUT_RETRY',
    },
    {
        'amount': 2899.0,
        'confidence': 0.39,
        'failure_reason': 'Synthetic demo: insufficient funds; payment link suggested',
        'action': ActionType.PAYMENT_LINK,
        'label': 'PAYMENT_LINK_REVIEW',
    },
    {
        'amount': 19999.0,
        'confidence': 0.31,
        'failure_reason': 'Synthetic demo: elevated fraud signal requires merchant review',
        'action': ActionType.STOP,
        'label': 'FRAUD_REVIEW',
    },
    {
        'amount': 499.0,
        'confidence': 0.44,
        'failure_reason': 'Synthetic demo: authentication evidence is incomplete',
        'action': ActionType.RETRY,
        'label': 'AUTHENTICATION_REVIEW',
    },
]


@router.post('/demo')
def create_demo_review_case(db: Session = Depends(get_db)):
    """Create a varied synthetic low-confidence case for the live governance demo.

    The scenario rotates deterministically from the current UTC second so
    repeated clicks do not always create the same amount/action. This endpoint
    never calls a payment provider or moves real money.
    """
    token = uuid.uuid4().hex[:12]
    scenario = DEMO_SCENARIOS[int(token[-4:], 16) % len(DEMO_SCENARIOS)]
    payment_id = f'demo_payment_{token}'
    case_id = f'demo_case_{token}'
    policy_id = f'demo_policy_{token}'
    execution_id = f'demo_execution_{token}'
    amount = scenario['amount']
    confidence = scenario['confidence']
    action = scenario['action']

    payment = Payment(
        id=payment_id,
        amount=amount,
        status=PaymentStatus.FAILED,
        payment_method='card',
        failure_reason=scenario['failure_reason'],
        retry_count=0,
    )
    case = RecoveryCase(
        id=case_id,
        payment_id=payment_id,
        revenue_at_risk=amount,
        recommended_action=action,
        ai_confidence=confidence,
    )
    policy = PolicyDecisionRecord(
        id=policy_id,
        recovery_case_id=case_id,
        decision=PolicyDecisionEnum.HUMAN_REVIEW,
        policy_version='v1.3',
        rules_triggered=['LOW_CONFIDENCE'],
    )

    db.add(payment)
    db.flush()
    db.add(case)
    db.flush()
    db.add(policy)
    db.flush()

    execution = ExecutionRecord(
        id=execution_id,
        policy_decision_id=policy_id,
        action=action,
        status='PENDING_HUMAN_REVIEW',
        idempotency_key=f'demo_review_{token}',
        result_details={
            'demo': True,
            'scenario': scenario['label'],
            'ai_confidence': confidence,
            'note': 'Synthetic case; no real-money movement',
        },
    )
    audit = AuditLog(
        id=f'audit_{uuid.uuid4().hex}',
        event_id=f'demo_created_{execution_id}',
        payment_id=payment_id,
        action=action.value,
        outcome='PENDING_HUMAN_REVIEW',
    )

    db.add(execution)
    db.add(audit)
    db.commit()
    return {
        'status': 'PENDING_HUMAN_REVIEW',
        'payment_id': payment_id,
        'case_id': case_id,
        'execution_id': execution_id,
        'amount': amount,
        'failure_reason': scenario['failure_reason'],
        'recommended_action': action.value,
        'ai_confidence': confidence,
        'scenario': scenario['label'],
        'policy_rules': ['LOW_CONFIDENCE'],
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
        result.append({'execution_id': row.id, 'case_id': case.id if case else None, 'payment_id': payment.id if payment else None, 'amount': payment.amount if payment else None, 'failure_reason': payment.failure_reason if payment else None, 'recommended_action': row.action.value if row.action else None, 'policy_decision_id': row.policy_decision_id, 'policy_rules': policy.rules_triggered if policy else [], 'created_at': row.created_at})
    return result


@router.post('/{execution_id}/decision')
def decide_review(execution_id: str, approved: bool, reviewer: str = 'merchant_reviewer', db: Session = Depends(get_db)):
    row = db.query(ExecutionRecord).filter(ExecutionRecord.id == execution_id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Review item not found')
    if row.status != 'PENDING_HUMAN_REVIEW':
        raise HTTPException(status_code=409, detail='Review item is no longer pending')
    policy = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.id == row.policy_decision_id).first()
    case = db.query(RecoveryCase).filter(RecoveryCase.id == (policy.recovery_case_id if policy else '')).first() if policy else None
    payment = db.query(Payment).filter(Payment.id == (case.payment_id if case else '')).first() if case else None
    if not policy or not case or not payment:
        raise HTTPException(status_code=409, detail='Incomplete recovery case')

    row.reviewed_by = reviewer
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_decision = 'APPROVED' if approved else 'REJECTED'
    if not approved:
        row.status = 'REJECTED_BY_HUMAN'
        row.result_details = {**(row.result_details or {}), 'reason': 'Merchant rejected recovery action'}
        db.add(AuditLog(id=f'audit_{uuid.uuid4().hex}', event_id=f'review_{row.id}', payment_id=payment.id, action=row.action.value, outcome='REJECTED_BY_HUMAN'))
        db.commit()
        return {'status': row.status, 'execution_id': row.id, 'review_decision': row.review_decision}

    row.status = 'PENDING'
    db.commit()
    result = executor.execute(db, {'case_id': case.id, 'payment_id': payment.id, 'amount': payment.amount, 'retry_count': payment.retry_count, 'recommended_action': row.action.value, 'ai_confidence': case.ai_confidence or 0.0}, 'allow', row.action.value, row.policy_decision_id)
    db.add(AuditLog(id=f'audit_{uuid.uuid4().hex}', event_id=f'review_{row.id}', payment_id=payment.id, action=row.action.value, outcome=result['status']))
    db.commit()
    return {'status': result['status'], 'execution_id': row.id, 'review_decision': row.review_decision, 'result_details': result.get('result_details', {})}
