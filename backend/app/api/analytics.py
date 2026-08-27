from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import Payment, RecoveryCase, PolicyDecisionRecord, ExecutionRecord, PaymentStatus, PolicyDecisionEnum
router = APIRouter()
@router.get('/dashboard')
def get_metrics(db: Session = Depends(get_db)):
    risk = db.query(func.sum(RecoveryCase.revenue_at_risk)).scalar() or 0.0
    recovered = db.query(func.sum(RecoveryCase.revenue_at_risk)).join(PolicyDecisionRecord, RecoveryCase.id == PolicyDecisionRecord.recovery_case_id).join(ExecutionRecord, PolicyDecisionRecord.id == ExecutionRecord.policy_decision_id).filter(ExecutionRecord.status == 'SUCCESS').scalar() or 0.0
    blocked = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.decision.in_([PolicyDecisionEnum.BLOCK, PolicyDecisionEnum.STOP])).count()
    return {'revenue_at_risk': round(risk, 2), 'revenue_recovered': round(recovered, 2), 'recovery_rate': round((recovered/risk*100) if risk>0 else 0, 2), 'unsafe_actions_blocked': blocked}
