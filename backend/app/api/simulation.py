from fastapi import APIRouter, Query
from ..simulation.evaluation import run_evaluation

router = APIRouter()


@router.post('/run')
def run_simulation(
    size: int = Query(10000, ge=100, le=100000),
    seed: int = Query(42, ge=0, le=2147483647),
):
    """Run an honest synthetic cohort evaluation; metrics are calculated at runtime."""
    return run_evaluation(size, seed=seed)
