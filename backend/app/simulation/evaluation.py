from statistics import mean, pstdev

from .baseline import run_baseline
from .recoverai import run_recoverai
from .generate_dataset import generate_dataset
from ..ml_model import ml_model


BENCHMARK_VERSION = 'channel-aware-v4-heldout'
DEFAULT_SEEDS = [42, 123, 456, 789, 2026]
TRAIN_SEED_OFFSET = 1_000_003


def _score_dataset(dataset, *, seed=None, source='synthetic', training_size=None):
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
        'training_dataset_size': training_size,
        'evaluation_protocol': 'model trained on an independent synthetic cohort and scored on this held-out cohort' if training_size else 'descriptive uploaded-dataset evaluation',
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
    if dataset_size < 100:
        raise ValueError('Evaluation cohort must contain at least 100 rows.')
    # Critical benchmark rule: never fit the ML model on the cohort whose
    # recovery value is being reported. This makes the money-recovery result
    # a genuine held-out evaluation instead of an in-sample estimate.
    training_size = max(1000, dataset_size)
    training = generate_dataset(training_size, seed=seed + TRAIN_SEED_OFFSET)
    evaluation = generate_dataset(dataset_size, seed=seed)
    ml_model.fit(training)
    return _score_dataset(evaluation, seed=seed, source='synthetic_heldout', training_size=training_size)


def run_dataset_evaluation(dataset):
    return _score_dataset(dataset, seed=None, source='uploaded_csv', training_size=None)


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
        'dataset_source': 'synthetic_multi_seed_heldout',
        'dataset_size_per_run': dataset_size,
        'training_dataset_size_per_run': max(1000, dataset_size),
        'evaluation_protocol': 'independent training cohort per seed; all reported recovery outcomes come from the held-out evaluation cohort',
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
