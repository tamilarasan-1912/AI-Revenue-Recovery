from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..engine.policy_engine import policy_engine
from ..ml_model import ml_model
from ..models import ImportedDatasetRow
from ..recovery_playbook import build_recovery_plan
from ..config import settings


def _latest_batch_id(db):
    latest = db.query(ImportedDatasetRow.batch_id).order_by(ImportedDatasetRow.created_at.desc(), ImportedDatasetRow.row_number.desc()).first()
    return latest[0] if latest else None


def _row_payload(row):
    payload = {
        'payment_id': row.payment_id,
        'amount': row.amount,
        'failure_reason': row.failure_reason,
        'retry_count': row.retry_count,
        'is_recoverable': row.is_recoverable,
    }
    optional_features = getattr(row, 'features', None)
    if isinstance(optional_features, dict):
        payload.update(optional_features)
    return payload


def evaluate_database_payments(db, limit: int = 1000, batch_id: str | None = None):
    active_batch = batch_id or _latest_batch_id(db)
    if not active_batch:
        return {
            'dataset_source': 'uploaded_csv_database', 'read_only': True, 'batch_id': None,
            'records_evaluated': 0, 'revenue_at_risk': 0.0, 'recoverable_revenue': 0.0,
            'predicted_recoverable_revenue': 0.0, 'recovered_revenue': 0.0, 'recovery_rate': 0.0,
            'recoverable_capture_rate': 0.0, 'recovered_records': 0,
            'policy_decisions': {'ALLOW': 0, 'BLOCK': 0, 'STOP': 0, 'HUMAN_REVIEW': 0},
            'action_counts': {}, 'recovery_stages': {}, 'records': [], 'ml_model': ml_model.status(),
        }

    safe_limit = max(1, min(int(limit), 1000))
    rows = db.query(ImportedDatasetRow).filter(ImportedDatasetRow.batch_id == active_batch).order_by(ImportedDatasetRow.row_number.asc()).limit(safe_limit).all()
    dataset_rows = [_row_payload(r) for r in rows]
    training_key = f'uploaded_batch:{active_batch}'
    if dataset_rows and (ml_model.classifier is None or ml_model.training_rows != len(dataset_rows) or ml_model.training_key != training_key):
        ml_model.fit(dataset_rows, training_key=training_key)
    predictions = ml_model.predict_many(dataset_rows)

    results, action_counts, recovery_stages = [], {}, {}
    counts = {'ALLOW': 0, 'BLOCK': 0, 'STOP': 0, 'HUMAN_REVIEW': 0}
    revenue_at_risk = recoverable_revenue = recovered_revenue = predicted_recoverable_revenue = 0.0
    recovered_records = 0

    for row, row_input, ml_prediction in zip(rows, dataset_rows, predictions):
        data = dict(row_input)
        data.update({'ml_recoverability': ml_prediction['recoverability_probability'], 'ml_confidence': ml_prediction['confidence']})
        risk = analyze_risk(data, use_external=False)
        strategy = recommend_strategy(data, risk, use_external=False)
        recovery_plan = build_recovery_plan(data, max_retries=settings.MAX_RETRIES, retry_delays_hours=settings.retry_delay_hours(), rescue_window_days=settings.RESCUE_WINDOW_DAYS)
        action = strategy['recommended_action']
        if action == 'RETRY' and not recovery_plan['retryable']:
            action = recovery_plan['recommended_action']
        case = {
            'case_id': row.id, 'payment_id': row.payment_id, 'amount': float(data['amount']),
            'recommended_action': action, 'ai_confidence': strategy['confidence'],
            'retry_count': int(data['retry_count']),
            'expected_recovery_value': ml_prediction.get('expected_recovery_amount') if ml_prediction.get('expected_recovery_amount') is not None else strategy.get('expected_recovery_value', 0.0),
            'fraud_signal': risk.get('fraud_signal', False),
            'ml_recoverability': ml_prediction['recoverability_probability'],
            'recovery_plan': recovery_plan,
        }
        policy = policy_engine.evaluate(case)
        decision = str(policy['decision']).lower()
        decision_key = decision.upper()
        if decision_key not in counts:
            decision_key = 'BLOCK'
        counts[decision_key] += 1
        action_counts[action] = action_counts.get(action, 0) + 1
        stage = recovery_plan['recovery_stage']
        recovery_stages[stage] = recovery_stages.get(stage, 0) + 1

        revenue_at_risk += float(data['amount'])
        if row.is_recoverable:
            recoverable_revenue += float(data['amount'])
        predicted_recoverable_revenue += float(data['amount']) * float(ml_prediction['recoverability_probability'])
        recovered = decision == 'allow' and bool(row.is_recoverable) and action in {'RETRY', 'PAYMENT_LINK'}
        if recovered:
            recovered_revenue += float(data['amount'])
            recovered_records += 1

        results.append({
            'row_id': row.id, 'payment_id': row.payment_id, 'amount': float(data['amount']),
            'failure_reason': data['failure_reason'], 'retry_count': int(data['retry_count']),
            'actual_is_recoverable': bool(row.is_recoverable), 'risk_score': risk.get('risk_score', 0.0),
            'failure_class': risk.get('failure_class', 'unknown'),
            'ml_recoverability': ml_prediction['recoverability_probability'],
            'ml_confidence': ml_prediction['confidence'],
            'expected_recovery_amount': ml_prediction.get('expected_recovery_amount'),
            'expected_recovery_rate': ml_prediction.get('expected_recovery_rate'),
            'ai_confidence': strategy.get('confidence', 0.0), 'recommended_action': action,
            'expected_recovery_value': case['expected_recovery_value'], 'policy_decision': decision,
            'rules_triggered': policy.get('rules_triggered', []), 'recovery_plan': recovery_plan,
            'recovered_in_simulation': recovered, 'source_batch': active_batch,
        })

    return {
        'dataset_source': 'uploaded_csv_database', 'read_only': True, 'batch_id': active_batch,
        'records_evaluated': len(results), 'revenue_at_risk': round(revenue_at_risk, 2),
        'recoverable_revenue': round(recoverable_revenue, 2),
        'predicted_recoverable_revenue': round(predicted_recoverable_revenue, 2),
        'recovered_revenue': round(recovered_revenue, 2),
        'recovery_rate': round((recovered_revenue / revenue_at_risk * 100) if revenue_at_risk else 0, 2),
        'recoverable_capture_rate': round((recovered_revenue / recoverable_revenue * 100) if recoverable_revenue else 0, 2),
        'recovered_records': recovered_records, 'policy_decisions': counts,
        'action_counts': action_counts, 'recovery_stages': recovery_stages,
        'records': results, 'ml_model': ml_model.status(),
    }
