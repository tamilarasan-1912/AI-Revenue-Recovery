from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..engine.policy_engine import policy_engine
from ..ml_model import ml_model
from ..models import ImportedDatasetRow


def evaluate_database_payments(db, limit: int = 1000, batch_id: str | None = None):
    query = db.query(ImportedDatasetRow)
    if batch_id:
        query = query.filter(ImportedDatasetRow.batch_id == batch_id)
    rows = query.order_by(ImportedDatasetRow.created_at.desc()).limit(limit).all()
    if rows and ml_model.training_rows == 0:
        ml_model.fit([{'payment_id': r.payment_id, 'amount': r.amount, 'failure_reason': r.failure_reason, 'retry_count': r.retry_count, 'is_recoverable': r.is_recoverable} for r in rows])

    results, counts, action_counts = [], {'ALLOW': 0, 'BLOCK': 0, 'STOP': 0, 'HUMAN_REVIEW': 0}, {}
    revenue_at_risk = recoverable_revenue = recovered_revenue = predicted_recoverable_revenue = 0.0
    recovered_records = 0

    for row in rows:
        data = {'payment_id': row.payment_id, 'amount': float(row.amount or 0), 'failure_reason': row.failure_reason or 'unknown', 'retry_count': int(row.retry_count or 0)}
        ml_prediction = ml_model.predict(data)
        data['ml_recoverability'] = ml_prediction['recoverability_probability']
        data['ml_confidence'] = ml_prediction['confidence']
        risk = analyze_risk(data, use_external=False)
        strategy = recommend_strategy(data, risk, use_external=False)
        action = strategy['recommended_action']
        case = {'case_id': row.id, 'payment_id': row.payment_id, 'amount': data['amount'], 'recommended_action': action, 'ai_confidence': strategy['confidence'], 'retry_count': data['retry_count'], 'expected_recovery_value': strategy.get('expected_recovery_value', 0.0), 'fraud_signal': risk.get('fraud_signal', False), 'ml_recoverability': ml_prediction['recoverability_probability']}
        policy = policy_engine.evaluate(case)
        decision = policy['decision']
        counts[decision] = counts.get(decision, 0) + 1
        action_counts[action] = action_counts.get(action, 0) + 1
        revenue_at_risk += data['amount']
        if row.is_recoverable:
            recoverable_revenue += data['amount']
        predicted_recoverable_revenue += data['amount'] * ml_prediction['recoverability_probability']
        recovered = decision == 'allow' and bool(row.is_recoverable) and action in {'RETRY', 'PAYMENT_LINK'}
        if recovered:
            recovered_revenue += data['amount']
            recovered_records += 1
        results.append({'row_id': row.id, 'payment_id': row.payment_id, 'amount': data['amount'], 'failure_reason': data['failure_reason'], 'retry_count': data['retry_count'], 'actual_is_recoverable': bool(row.is_recoverable), 'risk_score': risk.get('risk_score', 0.0), 'failure_class': risk.get('failure_class', 'unknown'), 'ml_recoverability': ml_prediction['recoverability_probability'], 'ml_confidence': ml_prediction['confidence'], 'ai_confidence': strategy.get('confidence', 0.0), 'recommended_action': action, 'expected_recovery_value': strategy.get('expected_recovery_value', 0.0), 'policy_decision': decision, 'rules_triggered': policy.get('rules_triggered', []), 'recovered_in_simulation': recovered, 'source_batch': row.batch_id})

    return {'dataset_source': 'uploaded_csv_database', 'read_only': True, 'batch_id': batch_id, 'records_evaluated': len(results), 'revenue_at_risk': round(revenue_at_risk, 2), 'recoverable_revenue': round(recoverable_revenue, 2), 'predicted_recoverable_revenue': round(predicted_recoverable_revenue, 2), 'recovered_revenue': round(recovered_revenue, 2), 'recovery_rate': round((recovered_revenue / revenue_at_risk * 100) if revenue_at_risk else 0, 2), 'recoverable_capture_rate': round((recovered_revenue / recoverable_revenue * 100) if recoverable_revenue else 0, 2), 'recovered_records': recovered_records, 'policy_decisions': counts, 'action_counts': action_counts, 'records': results, 'ml_model': ml_model.status()}
