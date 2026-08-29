from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import ImportedDatasetRow, ExecutionRecord, PolicyDecisionRecord, PolicyDecisionEnum, RecoveryCase

router = APIRouter()


@router.get('/dashboard')
def get_metrics(db: Session = Depends(get_db)):
    dataset_risk = db.query(func.sum(ImportedDatasetRow.amount)).scalar() or 0.0
    recoverable = db.query(func.sum(ImportedDatasetRow.amount)).filter(ImportedDatasetRow.is_recoverable.is_(True)).scalar() or 0.0
    recovered = db.query(func.sum(RecoveryCase.revenue_at_risk)).join(PolicyDecisionRecord, RecoveryCase.id == PolicyDecisionRecord.recovery_case_id).join(ExecutionRecord, PolicyDecisionRecord.id == ExecutionRecord.policy_decision_id).filter(ExecutionRecord.status == 'RECOVERED').scalar() or 0.0
    blocked = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.decision.in_([PolicyDecisionEnum.BLOCK, PolicyDecisionEnum.STOP])).count()
    human = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.decision == PolicyDecisionEnum.HUMAN_REVIEW).count()
    return {'dataset_loaded': dataset_risk > 0, 'dataset_records': db.query(ImportedDatasetRow.id).count(), 'revenue_at_risk': round(dataset_risk, 2), 'recoverable_revenue': round(recoverable, 2), 'revenue_recovered': round(recovered, 2), 'recovery_rate': round((recovered / dataset_risk * 100) if dataset_risk else 0, 2), 'unsafe_actions_blocked': blocked, 'human_escalations': human}
