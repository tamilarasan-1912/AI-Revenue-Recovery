from app.api.review import DEMO_SCENARIOS
from app.engine.policy_engine import policy_engine


def test_every_demo_scenario_matches_policy_engine():
    expected = {
        'BANK_TIMEOUT_ALLOW': 'allow',
        'INSUFFICIENT_FUNDS_PAYMENT_LINK': 'allow',
        'FRAUD_STOP': 'stop',
        'RETRY_EXHAUSTION_STOP': 'stop',
        'LOW_CONFIDENCE_HUMAN_REVIEW': 'human_review',
    }
    for scenario in DEMO_SCENARIOS:
        result = policy_engine.evaluate({
            'case_id': 'test',
            'payment_id': 'test',
            'amount': scenario['amount'],
            'recommended_action': scenario['action'].value,
            'ai_confidence': scenario['confidence'],
            'retry_count': scenario['retry_count'],
            'expected_recovery_value': scenario['expected_recovery_value'],
            'fraud_signal': scenario['fraud_signal'],
        })
        assert result['decision'] == expected[scenario['label']]
