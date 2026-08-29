from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..simulation.database_evaluation import evaluate_database_payments
from ..simulation.evaluation import run_dataset_evaluation, run_evaluation, run_multi_seed_evaluation

router = APIRouter()


@router.post('/run')
def run_simulation(
    size: int = Query(10000, ge=100, le=100000),
    seed: int = Query(42, ge=0, le=2147483647),
):
    return run_evaluation(size, seed=seed)


@router.post('/run-multi-seed')
def run_multi_seed(
    size: int = Query(10000, ge=100, le=50000),
    seeds: str = Query('42,123,456,789,2026'),
):
    """Run multiple independent cohorts and return mean/stddev evidence."""
    try:
        parsed = [int(s.strip()) for s in seeds.split(',') if s.strip()]
        return run_multi_seed_evaluation(size, parsed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post('/run-dataset')
def run_uploaded_dataset(payload: dict):
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
            'payment_id': str(row['payment_id']),
            'amount': amount,
            'failure_reason': str(row['failure_reason']),
            'retry_count': retry_count,
            'is_recoverable': str(row['is_recoverable']).strip().lower() in {'true', '1', 'yes', 'y'},
        })

    result = run_dataset_evaluation(normalized)
    result['dataset_source'] = 'uploaded_csv'
    return result


@router.get('/evaluate-database')
def evaluate_database(
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    return evaluate_database_payments(db, limit=limit)
