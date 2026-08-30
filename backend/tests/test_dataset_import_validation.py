from app.api.simulation import _normalize_rows


def test_boolean_string_is_normalized():
    rows = _normalize_rows([
        {
            'payment_id': 'pay_1',
            'amount': '100.5',
            'failure_reason': 'bank_timeout',
            'retry_count': '1',
            'is_recoverable': 'false',
        }
    ])
    assert rows[0]['is_recoverable'] is False
    assert rows[0]['amount'] == 100.5
    assert rows[0]['retry_count'] == 1


def test_missing_required_columns_are_reported():
    try:
        _normalize_rows([{
            'payment_id': 'pay_1',
            'amount': 100,
            'failure_reason': 'bank_timeout',
        }])
    except Exception as exc:
        assert 'missing' in str(exc.detail).lower()
        assert 'retry_count' in str(exc.detail)
        assert 'is_recoverable' in str(exc.detail)
    else:
        raise AssertionError('Expected validation failure')


def test_non_finite_amount_is_rejected():
    for value in ('nan', 'inf', '-inf'):
        try:
            _normalize_rows([{
                'payment_id': 'pay_bad',
                'amount': value,
                'failure_reason': 'bank_timeout',
                'retry_count': 0,
                'is_recoverable': True,
            }])
        except Exception as exc:
            assert 'non-finite' in str(exc.detail).lower()
        else:
            raise AssertionError(f'Expected non-finite amount {value!r} to be rejected')
