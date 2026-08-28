import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ExecutionRecord, PolicyDecisionRecord, RecoveryCase, Payment, AuditLog, PaymentStatus, ActionType, PolicyDecisionEnum
from ..engine.executor import executor

router = APIRouter()

@router.post('/demo')
def create_demo_review_case(db: Session = Depends(get_db)):
    """Create a synthetic low-confidence case for the live governance demo.

    This never calls a payment provider. It creates the same database records
    used by the review queue so the reviewer flow can be demonstrated safely.
    """
    token = uuid.uuid4().hex[:12]
    payment_id = f'demo_payment_{token}'
    case_id = f'demo_case_{token}'
    policy_id = f'demo_policy_{token}'
    execution_id = f'demo_execution_{token}'
    amount = 12500.0
    confidence = 0.42

    payment = Payment(
        id=payment_id,
        amount=amount,
        status=PaymentStatus.FAILED,
        payment_method='card',
        failure_reason='Synthetic demo: insufficient evidence for automatic recovery',
        retry_count=0,
    )
    case = RecoveryCase(
        id=case_id,
        payment_id=payment_id,
        revenue_at_risk=amount,
        recommended_action=ActionType.RETRY,
        ai_confidence=confidence,
    )
    policy = PolicyDecisionRecord(
        id=policy_id,
        recovery_case_id=case_id,
        decision=PolicyDecisionEnum.HUMAN_REVIEW,
        policy_version='v1.3',
        rules_triggered=['LOW_CONFIDENCE'],
    )

    # Flush the parent records first so PostgreSQL has the policy decision
    # available before the execution row is inserted. SQLAlchemy's add_all()
    # does not guarantee this dependency order during a flush.
    db.add(payment)
    db.add(case)
    db.add(policy)
    db.flush()

    execution = ExecutionRecord(
        id=execution_id,
        policy_decision_id=policy_id,
        action=ActionType.RETRY,
        status='PENDING_HUMAN_REVIEW',
        idempotency_key=f'demo_review_{token}',
        result_details={'demo': True, 'ai_confidence': confidence, 'note': 'Synthetic case; no real-money movement'},
    )
    audit = AuditLog(
        id=f'audit_{uuid.uuid4().hex}',
        event_id=f'demo_created_{execution_id}',
        payment_id=payment_id,
        action=ActionType.RETRY.value,
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
        'ai_confidence': confidence,
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
