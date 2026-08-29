from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..engine.policy_engine import policy_engine
from ..models import ImportedDatasetRow, Payment, PaymentStatus


def _action_would_recover(row, action: str) -> bool:
    """Use uploaded ground truth only after policy authorization for scoring."""
    if not row.get('is_recoverable', False):
        return False
    reason = str(row.get('failure_reason', '')).lower()
    if action == 'RETRY':
        return reason == 'bank_timeout'
    if action == 'PAYMENT_LINK':
        return reason in {'insufficient_funds', 'bank_timeout'}
    return False


def evaluate_database_payments(db, limit: int = 1000, batch_id: str | None = None):
    """Evaluate the selected imported CSV batch through the real AI + policy path.

    For imported data, is_recoverable is retained as hidden outcome ground truth:
    risk, strategy and policy never receive it. It is used only after authorization
    to calculate the observed synthetic recovery result.
    """
    if batch_id:
        source_rows = db.query(ImportedDatasetRow).filter(
            ImportedDatasetRow.batch_id == batch_id
        ).order_by(ImportedDatasetRow.row_number.asc()).limit(limit).all()
        rows = [{
            'payment_id': row.payment_id,
            'amount': float(row.amount or 0),
            'failure_reason': row.failure_reason or 'unknown',
            'retry_count': int(row.retry_count or 0),
            'is_recoverable': bool(row.is_recoverable),
        } for row in source_rows]
    else:
        payments = db.query(Payment).filter(Payment.status == PaymentStatus.FAILED).order_by(
            Payment.created_at.desc()
        ).limit(limit).all()
        rows = [{
            'payment_id': payment.id,
            'amount': float(payment.amount or 0),
            'failure_reason': payment.failure_reason or 'unknown',
            'retry_count': int(payment.retry_count or 0),
            'is_recoverable': False,
        } for payment in payments]

    results = []
    counts = {'ALLOW': 0, 'BLOCK': 0, 'STOP': 0, 'HUMAN_REVIEW': 0}
    action_counts = {}
    revenue_at_risk = 0.0
    recoverable_revenue = 0.0
    recovered_revenue = 0.0
    recovered_records = 0

    for row in rows:
        data = {
            'payment_id': row['payment_id'],
            'amount': row['amount'],
            'failure_reason': row['failure_reason'],
            'retry_count': row['retry_count'],
        }
        risk = analyze_risk(data, use_external=False)
        strategy = recommend_strategy(data, risk, use_external=False)
        action = strategy['recommended_action']
        case = {
            'case_id': row['payment_id'],
            'payment_id': row['payment_id'],
            'amount': data['amount'],
            'recommended_action': action,
            'ai_confidence': strategy['confidence'],
            'retry_count': data['retry_count'],
            'expected_recovery_value': strategy.get('expected_recovery_value', 0.0),
            'fraud_signal': risk.get('fraud_signal', False),
        }
        policy = policy_engine.evaluate(case)
        decision = policy['decision']
        counts[decision] = counts.get(decision, 0) + 1
        action_counts[action] = action_counts.get(action, 0) + 1
        revenue_at_risk += data['amount']
        if row['is_recoverable']:
            recoverable_revenue += data['amount']
        recovered = decision == 'allow' and _action_would_recover(row, action)
        if recovered:
            recovered_revenue += data['amount']
            recovered_records += 1
        results.append({
            'payment_id': row['payment_id'],
            'amount': data['amount'],
            'failure_reason': data['failure_reason'],
            'retry_count': data['retry_count'],
            'is_recoverable': row['is_recoverable'],
            'risk_score': risk.get('risk_score', 0.0),
            'failure_class': risk.get('failure_class', 'unknown'),
            'ai_confidence': strategy.get('confidence', 0.0),
            'recommended_action': action,
            'expected_recovery_value': strategy.get('expected_recovery_value', 0.0),
            'policy_decision': decision,
            'rules_triggered': policy.get('rules_triggered', []),
            'recovered_in_simulation': recovered,
            'source_batch': batch_id,
        })

    return {
        'dataset_source': 'uploaded_csv_database' if batch_id else 'database',
        'read_only': True,
        'batch_id': batch_id,
        'records_evaluated': len(results),
        'revenue_at_risk': round(revenue_at_risk, 2),
        'recoverable_revenue': round(recoverable_revenue, 2),
        'recovered_revenue': round(recovered_revenue, 2),
        'recovery_rate': round((recovered_revenue / revenue_at_risk * 100) if revenue_at_risk else 0, 2),
        'recoverable_capture_rate': round((recovered_revenue / recoverable_revenue * 100) if recoverable_revenue else 0, 2),
        'recovered_records': recovered_records,
        'policy_decisions': counts,
        'action_counts': action_counts,
        'records': results,
    }
