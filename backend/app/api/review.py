import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ExecutionRecord, PolicyDecisionRecord, RecoveryCase, Payment, ActionType
from ..engine.executor import executor

router = APIRouter()

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
            'created_at': row.created_at,
        })
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
        db.commit()
        return {'status': row.status, 'execution_id': row.id, 'review_decision': row.review_decision}

    # Human approval is still subject to the same bounded executor and Test Mode boundary.
    row.status = 'PENDING'
    db.commit()
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
    return {'status': result['status'], 'execution_id': row.id, 'review_decision': row.review_decision, 'result_details': result.get('result_details', {})}
