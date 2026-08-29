from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..engine.idempotency import idempotency_manager
from ..engine.policy_engine import policy_engine

router = APIRouter()


@router.post('/run')
def run_failure_injection(db: Session = Depends(get_db)):
    """Run safe, synthetic resilience checks without calling Razorpay."""
    case = {
        'case_id': 'failure_injection_demo',
        'payment_id': 'failure_injection_payment',
        'amount': 500.0,
        'retry_count': 3,
        'recommended_action': 'RETRY',
        'ai_confidence': 0.95,
        'expected_recovery_value': 400.0,
        'fraud_signal': False,
    }
    retry_policy = policy_engine.evaluate(case)

    key = idempotency_manager.make_key(case, 'RETRY')
    first = idempotency_manager.check_and_record(db, key, 'RETRY', 'failure_injection_policy')
    second = idempotency_manager.check_and_record(db, key, 'RETRY', 'failure_injection_policy')
    duplicate_protected = first is not None and second is not None and first.id == second.id

    return {
        'status': 'completed',
        'scenarios': {
            'retry_budget_exhausted': {
                'policy_decision': retry_policy['decision'],
                'rules_triggered': retry_policy['rules_triggered'],
                'expected': 'stop',
            },
            'duplicate_execution': {
                'same_execution_record': duplicate_protected,
                'execution_id': first.id if first else None,
                'expected': 'one execution record for repeated logical action',
            },
        },
        'execution_boundary': 'simulation only; no external payment call',
    }
