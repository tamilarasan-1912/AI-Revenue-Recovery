from statistics import mean, pstdev

from .baseline import run_baseline
from .recoverai import run_recoverai
from .generate_dataset import generate_dataset


BENCHMARK_VERSION = 'channel-aware-v3'
DEFAULT_SEEDS = [42, 123, 456, 789, 2026]


def _score_dataset(dataset, *, seed=None, source='synthetic'):
    dataset_size = len(dataset)
    base = run_baseline(dataset)
    rec = run_recoverai(dataset)
    baseline_revenue = base['revenue_recovered']
    incremental = rec['revenue_recovered'] - baseline_revenue
    improvement = (incremental / baseline_revenue * 100) if baseline_revenue > 0 else 0.0
    return {
        'benchmark_version': BENCHMARK_VERSION,
        'dataset_source': source,
        'dataset_size': dataset_size,
        'seed': seed,
        'baseline': base,
        'recoverai': rec,
        'revenue_at_risk': rec['revenue_at_risk'],
        'recoverable_revenue': rec['recoverable_revenue'],
        'incremental_revenue': round(incremental, 2),
        'improvement_percentage': round(improvement, 2),
        'human_review_rate': round((rec['human_reviews'] / dataset_size * 100) if dataset_size else 0, 2),
        'unsafe_block_rate': round((rec['unsafe_actions_blocked'] / dataset_size * 100) if dataset_size else 0, 2),
        'policy_stop_rate': round((rec['stopped_by_policy'] / dataset_size * 100) if dataset_size else 0, 2),
        'fraud_stop_rate': round((rec['fraud_stops'] / dataset_size * 100) if dataset_size else 0, 2),
        'intervention_execution_rate': round((rec['executed_interventions'] / dataset_size * 100) if dataset_size else 0, 2),
    }


def run_evaluation(dataset_size: int = 10000, seed: int = 42):
    dataset = generate_dataset(dataset_size, seed=seed)
    return _score_dataset(dataset, seed=seed, source='synthetic')


def run_dataset_evaluation(dataset):
    return _score_dataset(dataset, seed=None, source='uploaded_csv')


def run_multi_seed_evaluation(dataset_size: int = 10000, seeds=None):
    seeds = list(seeds or DEFAULT_SEEDS)
    if not 2 <= len(seeds) <= 10:
        raise ValueError('Use between 2 and 10 seeds.')
    if len(set(seeds)) != len(seeds):
        raise ValueError('Seeds must be unique.')

    runs = [run_evaluation(dataset_size, seed=int(seed)) for seed in seeds]
    inc = [r['incremental_revenue'] for r in runs]
    improvement = [r['improvement_percentage'] for r in runs]
    recovery = [r['recoverai']['revenue_recovery_rate'] for r in runs]
    baseline = [r['baseline']['revenue_recovery_rate'] for r in runs]
    review = [r['human_review_rate'] for r in runs]
    blocked = [r['unsafe_block_rate'] for r in runs]

    return {
        'benchmark_version': BENCHMARK_VERSION,
        'dataset_source': 'synthetic_multi_seed',
        'dataset_size_per_run': dataset_size,
        'seeds': seeds,
        'runs': runs,
        'aggregate': {
            'runs': len(runs),
            'total_transactions_evaluated': dataset_size * len(runs),
            'incremental_revenue_mean': round(mean(inc), 2),
            'incremental_revenue_stddev': round(pstdev(inc), 2),
            'improvement_percentage_mean': round(mean(improvement), 2),
            'improvement_percentage_stddev': round(pstdev(improvement), 2),
            'recoverai_revenue_recovery_rate_mean': round(mean(recovery), 2),
            'baseline_revenue_recovery_rate_mean': round(mean(baseline), 2),
            'human_review_rate_mean': round(mean(review), 2),
            'unsafe_block_rate_mean': round(mean(blocked), 2),
        },
    }
