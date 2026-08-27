from app.engine.idempotency import IdempotencyManager


def test_same_case_and_action_have_same_key():
    case = {'case_id': 'case_123', 'payment_id': 'pay_123', 'retry_count': 1}
    first = IdempotencyManager.make_key(case, 'RETRY')
    second = IdempotencyManager.make_key(case, 'RETRY')
    assert first == second


def test_different_attempts_have_different_retry_keys():
    case = {'case_id': 'case_123', 'payment_id': 'pay_123', 'retry_count': 1}
    next_attempt = {'case_id': 'case_123', 'payment_id': 'pay_123', 'retry_count': 2}
    assert IdempotencyManager.make_key(case, 'RETRY') != IdempotencyManager.make_key(next_attempt, 'RETRY')
