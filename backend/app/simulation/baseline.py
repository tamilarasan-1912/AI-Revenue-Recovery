def run_baseline(dataset):
    """Model a blind retry baseline with realistic channel mismatch.

    A retry can recover temporary bank failures, but it is intentionally
    ineffective for insufficient-funds failures where the customer needs a
    new payment attempt/link. Fraud is never recoverable by retry.
    Ground truth is used only for outcome scoring.
    """
    total = len(dataset)
    revenue_at_risk = sum(float(p.get('amount', 0) or 0) for p in dataset)
    recovered = 0
    revenue = 0.0
    unnecessary = 0

    for p in dataset:
        if p['retry_count'] >= 3:
            continue
        reason = str(p.get('failure_reason', '')).lower()
        recoverable = bool(p.get('is_recoverable', False))
        retry_effective = reason == 'bank_timeout'
        if recoverable and retry_effective:
            recovered += 1
            revenue += p['amount']
        else:
            unnecessary += 1

    return {
        'strategy': 'BLIND_RETRY',
        'total_transactions': total,
        'revenue_at_risk': round(revenue_at_risk, 2),
        'recovered_payments': recovered,
        'revenue_recovered': round(revenue, 2),
        'recovery_rate': round((recovered / total * 100) if total else 0, 2),
        'revenue_recovery_rate': round((revenue / revenue_at_risk * 100) if revenue_at_risk else 0, 2),
        'unnecessary_retries': unnecessary,
        'unsafe_actions_blocked': 0,
    }
