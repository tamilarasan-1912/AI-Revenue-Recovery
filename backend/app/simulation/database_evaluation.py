from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..engine.policy_engine import policy_engine
from ..models import Payment, PaymentStatus


def evaluate_database_payments(db, limit: int = 1000):
    """Read failed payments and evaluate recovery decisions without executing them.

    Database mode is intentionally read-only: no payment, execution, or audit
    records are mutated by this endpoint. Recovery success is not inferred
    because the Payment table does not contain hidden ground truth.
    """
    payments = (
        db.query(Payment)
        .filter(Payment.status == PaymentStatus.FAILED)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    counts = {
        'ALLOW': 0,
        'BLOCK': 0,
        'STOP': 0,
        'HUMAN_REVIEW': 0,
    }
    action_counts = {}
    revenue_at_risk = 0.0

    for payment in payments:
        data = {
            'payment_id': payment.id,
            'amount': float(payment.amount or 0),
            'failure_reason': payment.failure_reason or 'unknown',
            'retry_count': int(payment.retry_count or 0),
            'payment_method': payment.payment_method,
        }
        risk = analyze_risk(data, use_external=False)
        strategy = recommend_strategy(data, risk, use_external=False)
        case = {
            'case_id': payment.id,
            'payment_id': payment.id,
            'amount': data['amount'],
            'recommended_action': strategy['recommended_action'],
            'ai_confidence': strategy['confidence'],
            'retry_count': data['retry_count'],
            'expected_recovery_value': strategy.get('expected_recovery_value', 0.0),
            'fraud_signal': risk.get('fraud_signal', False),
        }
        policy = policy_engine.evaluate(case)
        decision = policy['decision']
        counts[decision] = counts.get(decision, 0) + 1
        action = strategy['recommended_action']
        action_counts[action] = action_counts.get(action, 0) + 1
        revenue_at_risk += data['amount']
        results.append({
            'payment_id': payment.id,
            'amount': data['amount'],
            'failure_reason': data['failure_reason'],
            'retry_count': data['retry_count'],
            'risk_score': risk.get('risk_score', 0.0),
            'failure_class': risk.get('failure_class', 'unknown'),
            'ai_confidence': strategy.get('confidence', 0.0),
            'recommended_action': action,
            'expected_recovery_value': strategy.get('expected_recovery_value', 0.0),
            'policy_decision': decision,
            'rules_triggered': policy.get('rules_triggered', []),
        })

    return {
        'dataset_source': 'database',
        'read_only': True,
        'records_evaluated': len(results),
        'revenue_at_risk': round(revenue_at_risk, 2),
        'policy_decisions': counts,
        'action_counts': action_counts,
        'records': results,
    }
