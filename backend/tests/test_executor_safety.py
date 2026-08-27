from app.config import settings
from app.engine.executor import RecoveryExecutor


def test_live_razorpay_key_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, 'ENABLE_RAZORPAY_TEST_ACTIONS', True)
    monkeypatch.setattr(settings, 'RAZORPAY_KEY_ID', 'rzp_live_should_never_be_used')
    monkeypatch.setattr(settings, 'RAZORPAY_KEY_SECRET', 'secret')

    result = RecoveryExecutor()._create_test_payment_link({'amount': 100, 'payment_id': 'pay_test'})

    assert result['mode'] == 'BLOCKED'
    assert 'Live Razorpay keys' in result['execution_boundary']
