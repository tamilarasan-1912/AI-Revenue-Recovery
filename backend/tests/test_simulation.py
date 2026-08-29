from app.simulation.evaluation import run_evaluation, run_multi_seed_evaluation


def test_benchmark_is_reproducible():
    first = run_evaluation(1000, seed=42)
    second = run_evaluation(1000, seed=42)
    assert first == second


def test_different_seed_changes_synthetic_cohort():
    first = run_evaluation(1000, seed=42)
    second = run_evaluation(1000, seed=123)
    assert first['seed'] != second['seed']
    assert first['revenue_at_risk'] != second['revenue_at_risk'] or first['recoverai'] != second['recoverai']


def test_benchmark_reports_required_track3_evidence():
    result = run_evaluation(1000, seed=42)
    assert result['dataset_size'] == 1000
    assert 'revenue_recovered' in result['recoverai']
    assert 'human_reviews' in result['recoverai']
    assert 'unsafe_actions_blocked' in result['recoverai']
    assert 'improvement_percentage' in result


def test_multi_seed_report_is_aggregated_not_cherry_picked():
    result = run_multi_seed_evaluation(500, [42, 123, 456])
    assert result['aggregate']['runs'] == 3
    assert result['aggregate']['total_transactions_evaluated'] == 1500
    assert 'incremental_revenue_mean' in result['aggregate']
    assert 'incremental_revenue_stddev' in result['aggregate']
    assert 'improvement_percentage_mean' in result['aggregate']
    assert len(result['runs']) == 3
