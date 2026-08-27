from fastapi import APIRouter, Query
from ..simulation.evaluation import run_evaluation

router = APIRouter()


@router.post('/run')
def run_simulation(size: int = Query(1000, ge=100, le=100000)):
    """Run an honest synthetic cohort evaluation; metrics are calculated at runtime."""
    return run_evaluation(size)
