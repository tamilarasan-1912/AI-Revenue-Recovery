import re
import uuid
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from ..models import ImportedDatasetRow, Payment, PaymentStatus
from ..database import get_db
from ..ml_model import ml_model
from ..recovery_playbook import build_recovery_plan
from ..simulation.database_evaluation import evaluate_database_payments
from ..simulation.evaluation import run_dataset_evaluation

router = APIRouter()
RUNTIME_EVALUATION_LIMIT = 1000


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
            amount = float(row['amount']); retry_count = int(row['retry_count'])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f'Row {index} has invalid amount or retry_count.')
        if amount < 0 or retry_count < 0:
            raise HTTPException(status_code=400, detail=f'Row {index} has negative amount or retry_count.')
        payment_id = str(row['payment_id']).strip(); failure_reason = str(row['failure_reason']).strip().lower()
        if not payment_id or not failure_reason:
            raise HTTPException(status_code=400, detail=f'Row {index} must have payment_id and failure_reason.')
        raw_label = row['is_recoverable']
        is_recoverable = raw_label if isinstance(raw_label, bool) else str(raw_label).strip().lower() in {'true', '1', 'yes', 'y'}
        item = dict(row)
        item.update({'payment_id': payment_id, 'amount': amount, 'failure_reason': failure_reason, 'retry_count': retry_count, 'is_recoverable': is_recoverable})
        normalized.append(item)
    return normalized


def _latest_batch_rows(db):
    latest = db.query(ImportedDatasetRow.batch_id).order_by(ImportedDatasetRow.created_at.desc(), ImportedDatasetRow.row_number.desc()).first()
    if not latest:
        return []
    rows = db.query(ImportedDatasetRow).filter(ImportedDatasetRow.batch_id == latest[0]).order_by(ImportedDatasetRow.row_number.asc()).limit(100000).all()
    payloads = []
    for r in rows:
        item = {'payment_id': r.payment_id, 'amount': r.amount, 'failure_reason': r.failure_reason, 'retry_count': r.retry_count, 'is_recoverable': r.is_recoverable}
        features = getattr(r, 'features', None)
        if isinstance(features, dict):
            item.update(features)
        payloads.append(item)
    return payloads


@router.get('/model-status')
def model_status(db: Session = Depends(get_db)):
    rows = _latest_batch_rows(db)
    if rows and ml_model.training_rows != len(rows):
        ml_model.fit(rows)
    return ml_model.status()


@router.post('/predict-recovery')
def predict_recovery(payload: dict, db: Session = Depends(get_db)):
    """Score one payment with the trained model and translate it into a safe recovery plan."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='Payment payload must be an object.')
    rows = _latest_batch_rows(db)
    if rows and ml_model.training_rows != len(rows):
        ml_model.fit(rows)
    try:
        prediction = ml_model.predict(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    plan = build_recovery_plan({**payload, 'ml_recoverability': prediction['recoverability_probability']})
    return {'prediction': prediction, 'recovery_plan': plan}


@router.post('/predict-batch')
def predict_batch(payload: dict, db: Session = Depends(get_db)):
    """Score a batch and return recovery recommendations without executing payments."""
    batch = payload.get('rows') if isinstance(payload, dict) else None
    if not isinstance(batch, list) or not batch:
        raise HTTPException(status_code=400, detail='rows must be a non-empty list.')
    if len(batch) > RUNTIME_EVALUATION_LIMIT:
        raise HTTPException(status_code=400, detail=f'Batch prediction is limited to {RUNTIME_EVALUATION_LIMIT} rows.')
    rows = _latest_batch_rows(db)
    if rows and ml_model.training_rows != len(rows):
        ml_model.fit(rows)
    try:
        predictions = ml_model.predict_many(batch)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    recommendations = []
    for row, prediction in zip(batch, predictions):
        recommendations.append({'payment_id': row.get('payment_id'), 'prediction': prediction, 'recovery_plan': build_recovery_plan({**row, 'ml_recoverability': prediction['recoverability_probability']})})
    return {'records': recommendations, 'ml_model': ml_model.status()}


@router.post('/run')
def run_simulation(db: Session = Depends(get_db)):
    result = evaluate_database_payments(db, limit=RUNTIME_EVALUATION_LIMIT)
    if result['records_evaluated'] == 0:
        raise HTTPException(status_code=409, detail='Upload a CSV dataset first. RecoverAI no longer uses pre-installed simulation data.')
    return {**result, 'dataset_source': 'uploaded_csv_database', 'evaluation_limit': RUNTIME_EVALUATION_LIMIT, 'ml_model': ml_model.status()}


@router.post('/run-multi-seed')
def run_multi_seed(seeds: str = Query('42,123,456,789,2026'), db: Session = Depends(get_db)):
    try:
        parsed = [int(s.strip()) for s in seeds.split(',') if s.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    result = evaluate_database_payments(db, limit=RUNTIME_EVALUATION_LIMIT)
    if result['records_evaluated'] == 0:
        raise HTTPException(status_code=409, detail='Upload a CSV dataset first.')
    return {**result, 'seeds': parsed, 'evaluation_limit': RUNTIME_EVALUATION_LIMIT, 'dataset_source': 'uploaded_csv_database', 'ml_model': ml_model.status()}


@router.post('/run-dataset')
def run_uploaded_dataset(payload: dict):
    normalized = _normalize_rows(payload)
    ml_status = ml_model.fit(normalized)
    result = run_dataset_evaluation(normalized[:RUNTIME_EVALUATION_LIMIT])
    result['dataset_source'] = 'uploaded_csv'
    result['evaluation_limit'] = min(len(normalized), RUNTIME_EVALUATION_LIMIT)
    result['records_preview'] = normalized[:100]
    result['ml_model'] = ml_status
    return result


@router.post('/import-dataset')
def import_uploaded_dataset(payload: dict, db: Session = Depends(get_db)):
    normalized = _normalize_rows(payload)
    batch_id = uuid.uuid4().hex[:10]
    imported_rows, payments = [], []
    for index, row in enumerate(normalized, start=1):
        features = {k: v for k, v in row.items() if k not in {'payment_id', 'amount', 'failure_reason', 'retry_count', 'is_recoverable'}}
        imported_rows.append(ImportedDatasetRow(id=f'csvrow_{batch_id}_{index}', batch_id=batch_id, row_number=index, payment_id=row['payment_id'], amount=row['amount'], failure_reason=row['failure_reason'], retry_count=row['retry_count'], is_recoverable=row['is_recoverable'], features=features or None))
        safe_id = re.sub(r'[^A-Za-z0-9_.-]+', '_', row['payment_id'])[:80] or f'row_{index}'
        payments.append(Payment(id=f'csv_{batch_id}_{index}_{safe_id}', amount=row['amount'], status=PaymentStatus.FAILED, payment_method=str(row.get('payment_method') or f'csv_demo:{batch_id}'), failure_reason=row['failure_reason'], retry_count=row['retry_count']))
    try:
        db.add_all(imported_rows); db.add_all(payments); db.commit()
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=f'Could not import dataset: {exc.__class__.__name__}')
    ml_status = ml_model.fit(normalized)
    evaluation = evaluate_database_payments(db, limit=min(len(normalized), RUNTIME_EVALUATION_LIMIT), batch_id=batch_id)
    return {'status': 'IMPORTED', 'batch_id': batch_id, 'records_imported': len(normalized), 'dataset_source': 'uploaded_csv_database', 'read_only_after_import': True, 'evaluation_limit': min(len(normalized), RUNTIME_EVALUATION_LIMIT), 'evaluation_is_bounded': len(normalized) > RUNTIME_EVALUATION_LIMIT, 'ml_model': ml_status, 'evaluation': evaluation}


@router.get('/evaluate-database')
def evaluate_database(limit: int = Query(RUNTIME_EVALUATION_LIMIT, ge=1, le=RUNTIME_EVALUATION_LIMIT), batch_id: str | None = Query(None), db: Session = Depends(get_db)):
    result = evaluate_database_payments(db, limit=limit, batch_id=batch_id)
    if result['records_evaluated'] == 0:
        raise HTTPException(status_code=409, detail='No uploaded CSV data is available. Upload a dataset first.')
    return {**result, 'ml_model': ml_model.status()}
