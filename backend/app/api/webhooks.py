import hashlib
import hmac
import json
import uuid
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Payment, PaymentStatus, RecoveryCase, PolicyDecisionRecord, AuditLog
from ..engine.policy_engine import policy_engine
from ..engine.executor import executor
from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..config import settings

router = APIRouter()


@router.post('/razorpay')
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get('x-razorpay-signature', '')
    if settings.RAZORPAY_WEBHOOK_SECRET:
        expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail='Invalid signature')

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid JSON')

    event_id = event.get('id') or f'evt_{uuid.uuid4().hex}'
    entity = event.get('entity') or event.get('payload', {}).get('payment', {}).get('entity', {}) or {}
    payment_id = entity.get('id', 'unknown')

    if db.query(AuditLog).filter(AuditLog.event_id == event_id).first():
        return {'status': 'ignored', 'reason': 'duplicate_event', 'event_id': event_id}

    status = entity.get('status', 'pending')
    db.add(AuditLog(id=f'audit_{uuid.uuid4().hex}', event_id=event_id, payment_id=payment_id,
                    action='WEBHOOK_RECEIVED', outcome=status))
    db.commit()

    if status != 'failed' or payment_id == 'unknown':
        return {'status': 'accepted', 'event_id': event_id, 'action': 'no_recovery_needed'}

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment:
        payment.status = PaymentStatus.FAILED
        payment.retry_count = int(entity.get('retry_count', payment.retry_count or 0))
        payment.failure_reason = entity.get('error_description', payment.failure_reason)
    else:
        payment = Payment(
            id=payment_id,
            amount=float(entity.get('amount', 0) or 0) / 100,
            status=PaymentStatus.FAILED,
            payment_method=entity.get('method', 'unknown'),
            failure_reason=entity.get('error_description', 'Unknown'),
            retry_count=int(entity.get('retry_count', 0) or 0),
        )
        db.add(payment)
    db.commit()

    pdata = {
        'payment_id': payment.id,
        'amount': payment.amount,
        'payment_method': payment.payment_method,
        'failure_reason': payment.failure_reason,
        'retry_count': payment.retry_count,
    }
    risk = analyze_risk(pdata)
    strat = recommend_strategy(pdata, risk)

    case_id = f'case_{uuid.uuid4().hex}'
    rcase = RecoveryCase(
        id=case_id,
        payment_id=payment.id,
        revenue_at_risk=min(float(risk.get('revenue_at_risk', payment.amount)), payment.amount),
        recommended_action=strat.get('recommended_action', 'STOP'),
        ai_confidence=float(strat.get('confidence', 0.5)),
    )
    db.add(rcase)
    db.commit()

    pcase = {
        'case_id': case_id,
        'payment_id': payment.id,
        'amount': payment.amount,
        'recommended_action': rcase.recommended_action.value if rcase.recommended_action else 'STOP',
        'ai_confidence': rcase.ai_confidence or 0.0,
        'retry_count': payment.retry_count,
        'expected_recovery_value': float(strat.get('expected_recovery_value', 0.0)),
        'fraud_signal': bool(risk.get('fraud_signal', False)),
    }
    policy = policy_engine.evaluate(pcase)
    policy_id = f'policy_{uuid.uuid4().hex}'
    db.add(PolicyDecisionRecord(
        id=policy_id,
        recovery_case_id=rcase.id,
        decision=policy['decision'],
        policy_version=policy['policy_version'],
        rules_triggered=policy['rules_triggered'],
    ))
    db.commit()

    action = rcase.recommended_action.value if rcase.recommended_action else 'STOP'
    exec_res = executor.execute(db, pcase, policy['decision'], action, policy_id)
    db.add(AuditLog(
        id=f'audit_{uuid.uuid4().hex}',
        event_id=event_id,
        payment_id=payment.id,
        action=action,
        outcome=exec_res['status'],
    ))
    db.commit()

    return {
        'status': 'processed',
        'event_id': event_id,
        'case_id': case_id,
        'policy': policy,
        'execution': exec_res,
    }
