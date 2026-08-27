import random, uuid
def generate_payment_event():
    amount = random.choice([199, 499, 999, 1499, 2999, 4999])
    failure_reason = random.choice(['bank_timeout', 'insufficient_funds', 'fraud_suspected'])
    is_recoverable = False if failure_reason == 'fraud_suspected' else random.random() > 0.4
    return {'payment_id': f'pay_{uuid.uuid4().hex[:10]}', 'amount': amount, 'failure_reason': failure_reason, 'retry_count': random.randint(0, 4), 'is_recoverable': is_recoverable}
def generate_dataset(size: int = 1000): return [generate_payment_event() for _ in range(size)]
