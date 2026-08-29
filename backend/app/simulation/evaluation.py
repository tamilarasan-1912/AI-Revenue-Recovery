from .baseline import run_baseline
from .recoverai import run_recoverai
from .generate_dataset import generate_dataset


BENCHMARK_VERSION = 'channel-aware-v2'


def _score_dataset(dataset, *, seed=None, source='synthetic'):
    """Score a supplied cohort using the same baseline and RecoverAI engines."""
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
    """Run the reproducible synthetic benchmark."""
    dataset = generate_dataset(dataset_size, seed=seed)
    return _score_dataset(dataset, seed=seed, source='synthetic')


def run_dataset_evaluation(dataset):
    """Run the same evaluation pipeline on caller-supplied records."""
    return _score_dataset(dataset, seed=None, source='uploaded_csv')
