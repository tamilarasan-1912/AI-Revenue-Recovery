from app.recovery_playbook import build_recovery_plan


def test_string_false_does_not_trigger_authentication_flow():
    plan = build_recovery_plan({
        'failure_reason': 'bank_timeout',
        'retry_count': 0,
        'authentication_required': 'false',
        'fraud_signal': 'false',
    })
    assert plan['failure_class'] == 'soft_decline'
    assert plan['recommended_action'] == 'RETRY'


def test_string_true_triggers_authentication_flow():
    plan = build_recovery_plan({
        'failure_reason': 'bank_timeout',
        'retry_count': 0,
        'authentication_required': 'true',
    })
    assert plan['failure_class'] == 'authentication_required'
    assert plan['recommended_action'] == 'PAYMENT_LINK'


def test_string_fraud_signal_always_stops():
    plan = build_recovery_plan({
        'failure_reason': 'payment_failed',
        'retry_count': 0,
        'fraud_signal': 'true',
    })
    assert plan['recovery_status'] == 'STOP'
    assert plan['recommended_action'] == 'STOP'
