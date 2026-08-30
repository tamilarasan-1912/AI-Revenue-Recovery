from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Payment, PaymentStatus, RecoveryCase, ImportedDatasetRow

router = APIRouter()


def _latest_batch_id(db):
    latest = db.query(ImportedDatasetRow.batch_id).order_by(ImportedDatasetRow.created_at.desc(), ImportedDatasetRow.row_number.desc()).first()
    return latest[0] if latest else None


def _active_payment_filter(batch_id):
    """Match payments imported for the active CSV batch.

    Older demo imports used ``csv_demo:<batch>`` as the payment method, while
    current imports use a deterministic ``csv_<batch>_...`` payment id. Keep
    both formats so existing deployed data remains visible.
    """
    return or_(
        Payment.id.like(f'csv_{batch_id}_%'),
        Payment.payment_method == f'csv_demo:{batch_id}',
    )


@router.get('/')
def list_payments(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    batch_id = _latest_batch_id(db)
    if not batch_id:
        return {'summary': {'total_events': 0, 'failed_payments': 0, 'successful_payments': 0, 'pending_payments': 0, 'recovery_cases': 0}, 'payments': []}

    source_filter = _active_payment_filter(batch_id)
    total = db.query(func.count(Payment.id)).filter(source_filter).scalar() or 0
    failed = db.query(func.count(Payment.id)).filter(source_filter, Payment.status == PaymentStatus.FAILED).scalar() or 0
    successful = db.query(func.count(Payment.id)).filter(source_filter, Payment.status == PaymentStatus.SUCCESS).scalar() or 0
    pending = db.query(func.count(Payment.id)).filter(source_filter, Payment.status == PaymentStatus.PENDING).scalar() or 0
    eligible = db.query(func.count(RecoveryCase.id)).join(Payment, RecoveryCase.payment_id == Payment.id).filter(source_filter).scalar() or 0
    rows = db.query(Payment).filter(source_filter).order_by(Payment.created_at.desc()).limit(limit).all()
    summary = {'total_events': total, 'failed_payments': failed, 'successful_payments': successful, 'pending_payments': pending, 'recovery_cases': eligible}
    return {'summary': summary, **summary, 'active_batch_id': batch_id, 'payments': [{'payment_id': p.id, 'amount': p.amount, 'status': p.status.value if p.status else None, 'payment_method': p.payment_method, 'failure_reason': p.failure_reason, 'retry_count': p.retry_count, 'created_at': p.created_at} for p in rows]}
