from app.engine.policy_engine import PolicyEngine


def test_fraud_always_stops_recovery():
    result = PolicyEngine().evaluate({
        'recommended_action': 'RETRY',
        'ai_confidence': 0.99,
        'retry_count': 0,
        'expected_recovery_value': 500,
        'fraud_signal': True,
    })
    assert result['decision'] == 'stop'
    assert 'FRAUD_SIGNAL' in result['rules_triggered']


def test_retry_limit_stops_action():
    result = PolicyEngine().evaluate({
        'recommended_action': 'RETRY',
        'ai_confidence': 0.95,
        'retry_count': 3,
        'expected_recovery_value': 500,
        'fraud_signal': False,
    })
    assert result['decision'] == 'stop'


def test_low_confidence_escalates_to_human():
    result = PolicyEngine().evaluate({
        'recommended_action': 'PAYMENT_LINK',
        'ai_confidence': 0.40,
        'retry_count': 0,
        'expected_recovery_value': 500,
        'fraud_signal': False,
    })
    assert result['decision'] == 'human_review'


def test_explicit_human_escalation_is_reviewable():
    result = PolicyEngine().evaluate({
        'recommended_action': 'HUMAN_ESCALATION',
        'ai_confidence': 0.90,
        'retry_count': 0,
        'expected_recovery_value': 500,
        'fraud_signal': False,
    })
    assert result['decision'] == 'human_review'
    assert 'EXPLICIT_HUMAN_ESCALATION' in result['rules_triggered']


def test_wait_is_not_an_automatic_money_action():
    result = PolicyEngine().evaluate({
        'recommended_action': 'WAIT',
        'ai_confidence': 0.95,
        'retry_count': 0,
        'expected_recovery_value': 500,
        'fraud_signal': False,
    })
    assert result['decision'] == 'human_review'
