from .baseline import run_baseline
from .recoverai import run_recoverai
from .generate_dataset import generate_dataset


def run_evaluation(dataset_size: int = 10000, seed: int = 42):
    dataset = generate_dataset(dataset_size, seed=seed)
    base = run_baseline(dataset)
    rec = run_recoverai(dataset)
    baseline_revenue = base['revenue_recovered']
    improvement = ((rec['revenue_recovered'] - baseline_revenue) / baseline_revenue * 100) if baseline_revenue > 0 else 0.0
    return {
        'dataset_size': dataset_size,
        'seed': seed,
        'baseline': base,
        'recoverai': rec,
        'incremental_revenue': round(rec['revenue_recovered'] - baseline_revenue, 2),
        'improvement_percentage': round(improvement, 2),
        'human_review_rate': round((rec['human_reviews'] / dataset_size * 100) if dataset_size else 0, 2),
        'unsafe_block_rate': round((rec['unsafe_actions_blocked'] / dataset_size * 100) if dataset_size else 0, 2),
    }
