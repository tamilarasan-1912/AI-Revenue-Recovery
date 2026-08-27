from app.agents.risk_agent import analyze_risk
from app.agents.strategy_agent import recommend_strategy
from app.engine.policy_engine import PolicyEngine


def test_fraud_is_stopped_before_low_confidence_review():
    result = PolicyEngine().evaluate({
        'recommended_action': 'PAYMENT_LINK',
        'ai_confidence': 0.2,
        'retry_count': 0,
        'expected_recovery_value': 100,
        'fraud_signal': True,
    })
    assert result['decision'] == 'stop'
    assert 'FRAUD_SIGNAL' in result['rules_triggered']


def test_retry_limit_stops_execution():
    result = PolicyEngine().evaluate({
        'recommended_action': 'RETRY',
        'ai_confidence': 0.95,
        'retry_count': 3,
        'expected_recovery_value': 100,
        'fraud_signal': False,
    })
    assert result['decision'] == 'stop'
    assert 'MAX_RETRIES_EXCEEDED' in result['rules_triggered']


def test_low_confidence_escalates():
    result = PolicyEngine().evaluate({
        'recommended_action': 'PAYMENT_LINK',
        'ai_confidence': 0.4,
        'retry_count': 0,
        'expected_recovery_value': 100,
        'fraud_signal': False,
    })
    assert result['decision'] == 'human_review'


def test_risk_is_contextual():
    fraud = analyze_risk({'amount': 1000, 'failure_reason': 'fraud_suspected', 'retry_count': 0})
    timeout = analyze_risk({'amount': 1000, 'failure_reason': 'bank_timeout', 'retry_count': 0})
    assert fraud['fraud_signal'] is True
    assert timeout['fraud_signal'] is False
    assert fraud['failure_class'] != timeout['failure_class']


def test_strategy_is_contextual():
    risk = analyze_risk({'amount': 999, 'failure_reason': 'insufficient_funds', 'retry_count': 0})
    strategy = recommend_strategy({'amount': 999, 'failure_reason': 'insufficient_funds', 'retry_count': 0}, risk)
    assert strategy['recommended_action'] == 'PAYMENT_LINK'
