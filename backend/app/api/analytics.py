from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import ImportedDatasetRow, ExecutionRecord, PolicyDecisionRecord, PolicyDecisionEnum, RecoveryCase

router = APIRouter()


def _latest_batch_id(db):
    latest = db.query(ImportedDatasetRow.batch_id).order_by(ImportedDatasetRow.created_at.desc(), ImportedDatasetRow.row_number.desc()).first()
    return latest[0] if latest else None


def _execution_source_batch(execution):
    return (execution.result_details or {}).get('source_batch')


def _active_batch_policy_decisions(db, batch_id):
    """Return policy decisions belonging to the currently uploaded dataset cohort.

    The dashboard is cohort-scoped. Historical executions must not inflate current
    human-review or blocked-action metrics after a new CSV is uploaded.
    """
    executions = db.query(ExecutionRecord).all()
    policy_ids = [
        execution.policy_decision_id
        for execution in executions
        if _execution_source_batch(execution) == batch_id and execution.policy_decision_id
    ]
    if not policy_ids:
        return []
    return db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.id.in_(policy_ids)).all()


@router.get('/dashboard')
def get_metrics(db: Session = Depends(get_db)):
    batch_id = _latest_batch_id(db)
    if not batch_id:
        return {
            'dataset_loaded': False,
            'dataset_batch_id': None,
            'dataset_records': 0,
            'revenue_at_risk': 0.0,
            'recoverable_revenue': 0.0,
            'revenue_recovered': 0.0,
            'recovery_rate': 0.0,
            'unsafe_actions_blocked': 0,
            'human_escalations': 0,
        }

    dataset_filter = ImportedDatasetRow.batch_id == batch_id
    dataset_risk = db.query(func.sum(ImportedDatasetRow.amount)).filter(dataset_filter).scalar() or 0.0
    recoverable = db.query(func.sum(ImportedDatasetRow.amount)).filter(
        dataset_filter,
        ImportedDatasetRow.is_recoverable.is_(True),
    ).scalar() or 0.0

    recovered = 0.0
    executions = db.query(ExecutionRecord).filter(ExecutionRecord.status == 'RECOVERED').all()
    for execution in executions:
        if _execution_source_batch(execution) != batch_id:
            continue
        case_id = db.query(PolicyDecisionRecord.recovery_case_id).filter(
            PolicyDecisionRecord.id == execution.policy_decision_id
        ).scalar()
        case = db.query(RecoveryCase).filter(RecoveryCase.id == (case_id or '')).first()
        if case:
            recovered += float(case.revenue_at_risk or 0)

    # Scope operational safety metrics to the active uploaded cohort. Previously
    # these counters queried the entire database, so resolved reviews from older
    # uploads remained visible on the dashboard while /review correctly showed an
    # empty pending queue.
    active_policies = _active_batch_policy_decisions(db, batch_id)
    blocked = sum(
        1 for policy in active_policies
        if policy.decision in (PolicyDecisionEnum.BLOCK, PolicyDecisionEnum.STOP)
    )

    active_policy_ids = {policy.id for policy in active_policies}
    human = sum(
        1
        for execution in db.query(ExecutionRecord).filter(
            ExecutionRecord.status == 'PENDING_HUMAN_REVIEW'
        ).all()
        if execution.policy_decision_id in active_policy_ids
        and _execution_source_batch(execution) == batch_id
    )

    return {
        'dataset_loaded': True,
        'dataset_batch_id': batch_id,
        'dataset_records': db.query(ImportedDatasetRow.id).filter(dataset_filter).count(),
        'revenue_at_risk': round(dataset_risk, 2),
        'recoverable_revenue': round(recoverable, 2),
        'revenue_recovered': round(recovered, 2),
        'recovery_rate': round((recovered / dataset_risk * 100) if dataset_risk else 0, 2),
        'unsafe_actions_blocked': blocked,
        'human_escalations': human,
    }
