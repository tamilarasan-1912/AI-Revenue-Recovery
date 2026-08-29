from ..agents.risk_agent import analyze_risk
from ..agents.strategy_agent import recommend_strategy
from ..engine.policy_engine import policy_engine
from ..ml_model import ml_model
from ..recovery_playbook import build_recovery_plan
from ..config import settings


def _simulated_action_succeeds(payment: dict, action: str) -> bool:
    if not payment.get('is_recoverable', False):
        return False
    reason = str(payment.get('failure_reason', '')).lower()
    if action == 'RETRY':
        return reason in {'bank_timeout', 'timeout', 'temporary_bank_degradation', 'issuer_unavailable'}
    if action == 'PAYMENT_LINK':
        return reason in {'insufficient_funds', 'bank_timeout', 'timeout', 'expired_card'}
    return False


def run_recoverai(dataset):
    total = len(dataset)
    use_ml = ml_model.model is not None
    revenue_at_risk = sum(float(p.get('amount', 0) or 0) for p in dataset)
    recoverable_revenue = sum(float(p.get('amount', 0) or 0) for p in dataset if p.get('is_recoverable'))
    recovered = 0; revenue = 0.0; unsafe_blocked = 0; human_reviews = 0; stopped = 0; fraud_stops = 0; retry_exhaustions = 0; executed_interventions = 0
    action_counts = {}; recovery_stages = {}

    predictions = ml_model.predict_many(dataset) if use_ml else [None] * total
    for p, ml_prediction in zip(dataset, predictions):
        model_input = dict(p)
        if ml_prediction is not None:
            model_input.update({'ml_recoverability': ml_prediction['recoverability_probability'], 'ml_confidence': ml_prediction['confidence']})
        risk = analyze_risk(model_input, use_external=False)
        strat = recommend_strategy(model_input, risk, use_external=False)
        plan = build_recovery_plan(model_input, max_retries=settings.MAX_RETRIES, retry_delays_hours=settings.retry_delay_hours(), rescue_window_days=settings.RESCUE_WINDOW_DAYS)
        action = strat['recommended_action']
        if action == 'RETRY' and not plan['retryable']:
            action = plan['recommended_action']
        recovery_stages[plan['recovery_stage']] = recovery_stages.get(plan['recovery_stage'], 0) + 1
        case = {'case_id': p['payment_id'], 'payment_id': p['payment_id'], 'amount': p['amount'], 'recommended_action': action, 'ai_confidence': strat['confidence'], 'retry_count': p['retry_count'], 'expected_recovery_value': strat.get('expected_recovery_value', 0.0), 'fraud_signal': risk.get('fraud_signal', False), 'recovery_plan': plan}
        policy = policy_engine.evaluate(case)
        action_counts[action] = action_counts.get(action, 0) + 1
        if policy['decision'] in ['block', 'stop']:
            stopped += 1
            if 'FRAUD_SIGNAL' in policy['rules_triggered']: fraud_stops += 1
            if 'MAX_RETRIES_EXCEEDED' in policy['rules_triggered']: retry_exhaustions += 1
            if not p.get('is_recoverable', False) or p.get('failure_reason') == 'fraud_suspected': unsafe_blocked += 1
            continue
        if policy['decision'] == 'human_review':
            human_reviews += 1
            continue
        if action in {'RETRY', 'PAYMENT_LINK'}:
            executed_interventions += 1
            if _simulated_action_succeeds(p, action): recovered += 1; revenue += p['amount']

    revenue_recovery_rate = (revenue / revenue_at_risk * 100) if revenue_at_risk else 0.0
    capture_rate = (revenue / recoverable_revenue * 100) if recoverable_revenue else 0.0
    return {'strategy': 'RECOVERAI_ML' if use_ml else 'RECOVERAI_POLICY', 'total_transactions': total, 'revenue_at_risk': round(revenue_at_risk, 2), 'recoverable_revenue': round(recoverable_revenue, 2), 'recovered_payments': recovered, 'revenue_recovered': round(revenue, 2), 'recovery_rate': round((recovered / total * 100) if total else 0, 2), 'revenue_recovery_rate': round(revenue_recovery_rate, 2), 'recoverable_revenue_capture_rate': round(capture_rate, 2), 'unsafe_actions_blocked': unsafe_blocked, 'human_reviews': human_reviews, 'stopped_by_policy': stopped, 'fraud_stops': fraud_stops, 'retry_exhaustions': retry_exhaustions, 'executed_interventions': executed_interventions, 'action_counts': action_counts, 'recovery_stages': recovery_stages, 'ml_model': ml_model.status()}
