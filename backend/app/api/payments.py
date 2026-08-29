from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Payment, PaymentStatus, RecoveryCase

router = APIRouter()


@router.get('/')
def list_payments(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    total = db.query(func.count(Payment.id)).scalar() or 0
    failed = db.query(func.count(Payment.id)).filter(Payment.status == PaymentStatus.FAILED).scalar() or 0
    successful = db.query(func.count(Payment.id)).filter(Payment.status == PaymentStatus.SUCCESS).scalar() or 0
    pending = db.query(func.count(Payment.id)).filter(Payment.status == PaymentStatus.PENDING).scalar() or 0
    eligible = db.query(func.count(RecoveryCase.id)).join(Payment, RecoveryCase.payment_id == Payment.id).filter(Payment.status == PaymentStatus.FAILED).scalar() or 0

    rows = db.query(Payment).order_by(Payment.created_at.desc()).limit(limit).all()
    return {
        'summary': {
            'total_events': total,
            'failed_payments': failed,
            'successful_payments': successful,
            'pending_payments': pending,
            'recovery_cases': eligible,
        },
        'payments': [
            {
                'payment_id': p.id,
                'amount': p.amount,
                'status': p.status.value if p.status else None,
                'payment_method': p.payment_method,
                'failure_reason': p.failure_reason,
                'retry_count': p.retry_count,
                'created_at': p.created_at,
            }
            for p in rows
        ],
    }
