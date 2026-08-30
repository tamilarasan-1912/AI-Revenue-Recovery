import random


AMOUNTS = [199, 499, 999, 1499, 2999, 4999, 9999]
FAILURES = ['bank_timeout', 'insufficient_funds', 'fraud_suspected']


def generate_payment_event(rng: random.Random | None = None):
    rng = rng or random.Random()
    amount = rng.choice(AMOUNTS)
    failure_reason = rng.choice(FAILURES)
    # Synthetic ground truth is used only for evaluation; the agents do not receive it.
    is_recoverable = False if failure_reason == 'fraud_suspected' else rng.random() > 0.35
    # Use the seeded RNG for IDs too. UUIDs made the supposedly reproducible
    # benchmark produce different ML training identities on every run.
    payment_nonce = rng.getrandbits(48)
    return {
        'payment_id': f'pay_{payment_nonce:012x}',
        'amount': amount,
        'failure_reason': failure_reason,
        'retry_count': rng.randint(0, 4),
        'is_recoverable': is_recoverable,
    }


def generate_dataset(size: int = 1000, seed: int = 42):
    rng = random.Random(seed)
    return [generate_payment_event(rng) for _ in range(size)]
