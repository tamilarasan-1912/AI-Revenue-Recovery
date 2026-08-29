from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import ImportedDatasetRow, ExecutionRecord, PolicyDecisionRecord, PolicyDecisionEnum, RecoveryCase

router = APIRouter()


def _latest_batch_id(db):
    latest = db.query(ImportedDatasetRow.batch_id).order_by(ImportedDatasetRow.created_at.desc(), ImportedDatasetRow.row_number.desc()).first()
    return latest[0] if latest else None


@router.get('/dashboard')
def get_metrics(db: Session = Depends(get_db)):
    batch_id = _latest_batch_id(db)
    if not batch_id:
        return {'dataset_loaded': False, 'dataset_batch_id': None, 'dataset_records': 0, 'revenue_at_risk': 0.0, 'recoverable_revenue': 0.0, 'revenue_recovered': 0.0, 'recovery_rate': 0.0, 'unsafe_actions_blocked': 0, 'human_escalations': 0}
    dataset_filter = ImportedDatasetRow.batch_id == batch_id
    dataset_risk = db.query(func.sum(ImportedDatasetRow.amount)).filter(dataset_filter).scalar() or 0.0
    recoverable = db.query(func.sum(ImportedDatasetRow.amount)).filter(dataset_filter, ImportedDatasetRow.is_recoverable.is_(True)).scalar() or 0.0
    recovered = 0.0
    executions = db.query(ExecutionRecord).filter(ExecutionRecord.status == 'RECOVERED').all()
    for execution in executions:
        if (execution.result_details or {}).get('source_batch') == batch_id:
            case = db.query(RecoveryCase).filter(RecoveryCase.id == (db.query(PolicyDecisionRecord.recovery_case_id).filter(PolicyDecisionRecord.id == execution.policy_decision_id).scalar() or '')).first()
            if case: recovered += float(case.revenue_at_risk or 0)
    blocked = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.decision.in_([PolicyDecisionEnum.BLOCK, PolicyDecisionEnum.STOP])).count()
    human = db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.decision == PolicyDecisionEnum.HUMAN_REVIEW).count()
    return {'dataset_loaded': True, 'dataset_batch_id': batch_id, 'dataset_records': db.query(ImportedDatasetRow.id).filter(dataset_filter).count(), 'revenue_at_risk': round(dataset_risk, 2), 'recoverable_revenue': round(recoverable, 2), 'revenue_recovered': round(recovered, 2), 'recovery_rate': round((recovered / dataset_risk * 100) if dataset_risk else 0, 2), 'unsafe_actions_blocked': blocked, 'human_escalations': human}
