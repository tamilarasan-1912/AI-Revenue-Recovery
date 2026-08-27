from .baseline import run_baseline
from .recoverai import run_recoverai
from .generate_dataset import generate_dataset
def run_evaluation(dataset_size: int = 1000):
    dataset = generate_dataset(dataset_size)
    base = run_baseline(dataset); rec = run_recoverai(dataset)
    imp = ((rec['revenue_recovered'] - base['revenue_recovered']) / base['revenue_recovered'] * 100) if base['revenue_recovered'] > 0 else 100.0
    return {'dataset_size': dataset_size, 'baseline': base, 'recoverai': rec, 'improvement_percentage': round(imp, 2)}
