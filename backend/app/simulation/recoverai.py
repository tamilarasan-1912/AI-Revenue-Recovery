from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..engine.policy_engine import policy_engine


def run_recoverai(dataset):
    total = len(dataset)
    recovered = 0
    revenue = 0.0
    unsafe_blocked = 0
    human_reviews = 0
    stopped = 0
    action_counts = {}

    for p in dataset:
        risk = analyze_risk(p)
        strat = recommend_strategy(p, risk)
        action = strat['recommended_action']
        case = {
            'case_id': p['payment_id'],
            'payment_id': p['payment_id'],
            'amount': p['amount'],
            'recommended_action': action,
            'ai_confidence': strat['confidence'],
            'retry_count': p['retry_count'],
            'expected_recovery_value': strat.get('expected_recovery_value', 0.0),
            'fraud_signal': risk.get('fraud_signal', False),
        }
        policy = policy_engine.evaluate(case)
        action_counts[action] = action_counts.get(action, 0) + 1

        if policy['decision'] in ['block', 'stop']:
            stopped += 1
            if action == 'RETRY' and not p['is_recoverable']:
                unsafe_blocked += 1
            continue
        if policy['decision'] == 'human_review':
            human_reviews += 1
            continue

        if action in {'RETRY', 'PAYMENT_LINK'} and p['is_recoverable']:
            recovered += 1
            revenue += p['amount']

    return {
        'strategy': 'RECOVERAI',
        'total_transactions': total,
        'recovered_payments': recovered,
        'revenue_recovered': round(revenue, 2),
        'recovery_rate': round((recovered / total * 100) if total else 0, 2),
        'unsafe_actions_blocked': unsafe_blocked,
        'human_reviews': human_reviews,
        'stopped_by_policy': stopped,
        'action_counts': action_counts,
    }
