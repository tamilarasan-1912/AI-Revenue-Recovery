import uuid
import re
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Payment, PaymentStatus
from ..simulation.database_evaluation import evaluate_database_payments
from ..simulation.evaluation import run_dataset_evaluation, run_evaluation, run_multi_seed_evaluation

router = APIRouter()


def _normalize_rows(payload: dict):
    rows = payload.get('rows') if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=400, detail='Upload a non-empty dataset.')
    if len(rows) > 100000:
        raise HTTPException(status_code=400, detail='Dataset cannot exceed 100,000 rows.')
    required = {'payment_id', 'amount', 'failure_reason', 'retry_count', 'is_recoverable'}
    normalized = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise HTTPException(status_code=400, detail=f'Row {index} is not an object.')
        missing = sorted(required - set(row.keys()))
        if missing:
            raise HTTPException(status_code=400, detail=f'Row {index} is missing: {", ".join(missing)}')
        try:
            amount = float(row['amount'])
            retry_count = int(row['retry_count'])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f'Row {index} has invalid amount or retry_count.')
        if amount < 0 or retry_count < 0:
            raise HTTPException(status_code=400, detail=f'Row {index} has negative amount or retry_count.')
        normalized.append({
            'payment_id': str(row['payment_id']).strip(),
            'amount': amount,
            'failure_reason': str(row['failure_reason']).strip(),
            'retry_count': retry_count,
            'is_recoverable': str(row['is_recoverable']).strip().lower() in {'true', '1', 'yes', 'y'},
        })
    return normalized


@router.post('/run')
def run_simulation(size: int = Query(10000, ge=100, le=100000), seed: int = Query(42, ge=0, le=2147483647)):
    return run_evaluation(size, seed=seed)


@router.post('/run-multi-seed')
def run_multi_seed(size: int = Query(10000, ge=100, le=50000), seeds: str = Query('42,123,456,789,2026')):
    try:
        parsed = [int(s.strip()) for s in seeds.split(',') if s.strip()]
        return run_multi_seed_evaluation(size, parsed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post('/run-dataset')
def run_uploaded_dataset(payload: dict):
    normalized = _normalize_rows(payload)
    result = run_dataset_evaluation(normalized)
    result['dataset_source'] = 'uploaded_csv'
    result['records_preview'] = normalized[:100]
    return result


@router.post('/import-dataset')
def import_uploaded_dataset(payload: dict, db: Session = Depends(get_db)):
    """Explicitly copy an uploaded CSV into the demo PostgreSQL dataset.

    This never calls a payment provider. Imported records are tagged with a
    unique batch id so the UI can evaluate exactly the dataset just imported.
    """
    normalized = _normalize_rows(payload)
    batch_id = uuid.uuid4().hex[:10]
    inserted = []
    for index, row in enumerate(normalized, start=1):
        safe_id = re.sub(r'[^A-Za-z0-9_.-]+', '_', row['payment_id'])[:80] or f'row_{index}'
        payment_id = f'csv_{batch_id}_{index}_{safe_id}'
        inserted.append(Payment(
            id=payment_id,
            amount=row['amount'],
            status=PaymentStatus.FAILED,
            payment_method=f'csv_demo:{batch_id}',
            failure_reason=row['failure_reason'],
            retry_count=row['retry_count'],
        ))
    try:
        db.add_all(inserted)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f'Could not import dataset: {exc.__class__.__name__}')
    return {
        'status': 'IMPORTED',
        'batch_id': batch_id,
        'records_imported': len(inserted),
        'dataset_source': 'uploaded_csv_database',
        'read_only_after_import': True,
    }


@router.get('/evaluate-database')
def evaluate_database(
    limit: int = Query(1000, ge=1, le=10000),
    batch_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return evaluate_database_payments(db, limit=limit, batch_id=batch_id)
