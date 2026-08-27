from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..engine.policy_engine import policy_engine
import random
def run_recoverai(dataset):
    total = len(dataset); recovered = 0; revenue = 0.0; unsafe_blocked = 0
    for p in dataset:
        risk = analyze_risk(p); strat = recommend_strategy(p, risk)
        case = {'payment_id': p['payment_id'], 'recommended_action': strat['recommended_action'], 'ai_confidence': strat['confidence'], 'retry_count': p['retry_count'], 'expected_recovery_value': strat.get('expected_recovery_value', 0.0), 'fraud_signal': risk.get('fraud_signal', False)}
        policy = policy_engine.evaluate(case)
        if policy['decision'] in ['block', 'stop']:
            if strat['recommended_action'] == 'RETRY' and not p['is_recoverable']: unsafe_blocked += 1
            continue
        if strat['recommended_action'] == 'RETRY' and p['is_recoverable']: recovered += 1; revenue += p['amount']
        elif strat['recommended_action'] == 'PAYMENT_LINK' and p['is_recoverable']: recovered += 1; revenue += p['amount']
    return {'strategy': 'RECOVERAI', 'total_transactions': total, 'recovered_payments': recovered, 'revenue_recovered': round(revenue, 2), 'recovery_rate': round((recovered/total*100) if total>0 else 0, 2), 'unsafe_actions_blocked': unsafe_blocked}
