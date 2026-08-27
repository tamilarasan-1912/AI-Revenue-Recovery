def run_baseline(dataset):
    total = len(dataset); recovered = 0; revenue = 0.0; unnecessary = 0
    for p in dataset:
        if p['retry_count'] < 3:
            if p['is_recoverable']: recovered += 1; revenue += p['amount']
            else: unnecessary += 1
    return {'strategy': 'BLIND_RETRY', 'total_transactions': total, 'recovered_payments': recovered, 'revenue_recovered': round(revenue, 2), 'recovery_rate': round((recovered/total*100) if total>0 else 0, 2), 'unnecessary_retries': unnecessary, 'unsafe_actions_blocked': 0}
