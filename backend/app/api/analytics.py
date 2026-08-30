from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import ImportedDatasetRow, ExecutionRecord, PolicyDecisionRecord, PolicyDecisionEnum, RecoveryCase
from ..simulation.database_evaluation import evaluate_database_payments

router = APIRouter()


def _latest_batch_id(db):
    latest = db.query(ImportedDatasetRow.batch_id).order_by(ImportedDatasetRow.created_at.desc(), ImportedDatasetRow.row_number.desc()).first()
    return latest[0] if latest else None


def _execution_source_batch(execution):
    return (execution.result_details or {}).get('source_batch')


def _active_batch_policy_decisions(db, batch_id):
    """Return persisted policy decisions belonging to the active uploaded cohort."""
    executions = db.query(ExecutionRecord).all()
    policy_ids = [
        execution.policy_decision_id
        for execution in executions
        if _execution_source_batch(execution) == batch_id and execution.policy_decision_id
    ]
    if not policy_ids:
        return []
    return db.query(PolicyDecisionRecord).filter(PolicyDecisionRecord.id.in_(policy_ids)).all()


def _pending_human_reviews(db, batch_id):
    """Count only actionable, currently pending merchant reviews for the active cohort."""
    active_policy_ids = {policy.id for policy in _active_batch_policy_decisions(db, batch_id)}
    if not active_policy_ids:
        return 0
    return sum(
        1
        for execution in db.query(ExecutionRecord).filter(
            ExecutionRecord.status == 'PENDING_HUMAN_REVIEW'
        ).all()
        if execution.policy_decision_id in active_policy_ids
        and _execution_source_batch(execution) == batch_id
    )


@router.get('/dashboard')
def get_metrics(db: Session = Depends(get_db)):
    batch_id = _latest_batch_id(db)
    if not batch_id:
        return {
            'dataset_loaded': False,
            'dataset_batch_id': None,
            'dataset_records': 0,
            'ai_analyzed': 0,
            'policy_evaluated_records': 0,
            'revenue_at_risk': 0.0,
            'recoverable_revenue': 0.0,
            'predicted_recoverable_revenue': 0.0,
            'revenue_recovered': 0.0,
            'recovery_rate': 0.0,
            'recoverable_capture_rate': 0.0,
            'unsafe_actions_blocked': 0,
            'human_escalations': 0,
            'policy_decisions': {'ALLOW': 0, 'BLOCK': 0, 'STOP': 0, 'HUMAN_REVIEW': 0},
        }

    dataset_filter = ImportedDatasetRow.batch_id == batch_id
    dataset_records = db.query(ImportedDatasetRow.id).filter(dataset_filter).count()
    dataset_risk = db.query(func.sum(ImportedDatasetRow.amount)).filter(dataset_filter).scalar() or 0.0
    recoverable = db.query(func.sum(ImportedDatasetRow.amount)).filter(
        dataset_filter,
        ImportedDatasetRow.is_recoverable.is_(True),
    ).scalar() or 0.0

    # Run the same read-only cohort evaluation used by Simulation Lab. This keeps
    # the overview funnel mathematically tied to the ML + AI + policy pipeline,
    # rather than deriving Policy Allowed as `rows - review - blocked`, which can
    # silently misreport outcomes when new policy states are introduced.
    evaluation = evaluate_database_payments(db, limit=min(dataset_records, 1000), batch_id=batch_id)
    policy_decisions = {
        'ALLOW': int(evaluation.get('policy_decisions', {}).get('ALLOW', 0)),
        'BLOCK': int(evaluation.get('policy_decisions', {}).get('BLOCK', 0)),
        'STOP': int(evaluation.get('policy_decisions', {}).get('STOP', 0)),
        'HUMAN_REVIEW': int(evaluation.get('policy_decisions', {}).get('HUMAN_REVIEW', 0)),
    }

    # Operational metric: unlike the simulation distribution above, this is the
    # number of persisted cases that are actually waiting for merchant action.
    pending_human = _pending_human_reviews(db, batch_id)

    return {
        'dataset_loaded': True,
        'dataset_batch_id': batch_id,
        'dataset_records': dataset_records,
        'ai_analyzed': int(evaluation.get('records_evaluated', 0)),
        'policy_evaluated_records': int(evaluation.get('records_evaluated', 0)),
        'revenue_at_risk': round(float(evaluation.get('revenue_at_risk', dataset_risk)), 2),
        'recoverable_revenue': round(float(evaluation.get('recoverable_revenue', recoverable)), 2),
        'predicted_recoverable_revenue': round(float(evaluation.get('predicted_recoverable_revenue', 0.0)), 2),
        'revenue_recovered': round(float(evaluation.get('recovered_revenue', 0.0)), 2),
        'recovery_rate': round(float(evaluation.get('recovery_rate', 0.0)), 2),
        'recoverable_capture_rate': round(float(evaluation.get('recoverable_capture_rate', 0.0)), 2),
        'unsafe_actions_blocked': policy_decisions['BLOCK'] + policy_decisions['STOP'],
        'human_escalations': pending_human,
        'policy_decisions': policy_decisions,
    }
