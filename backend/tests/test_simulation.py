from app.simulation.evaluation import run_evaluation


def test_benchmark_is_reproducible():
    first = run_evaluation(1000, seed=42)
    second = run_evaluation(1000, seed=42)
    assert first == second


def test_benchmark_reports_required_track3_evidence():
    result = run_evaluation(1000, seed=42)
    assert result['dataset_size'] == 1000
    assert 'revenue_recovered' in result['recoverai']
    assert 'human_reviews' in result['recoverai']
    assert 'unsafe_actions_blocked' in result['recoverai']
    assert 'improvement_percentage' in result
