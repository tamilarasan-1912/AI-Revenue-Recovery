import uuid
from ..models import ActionType
from .idempotency import idempotency_manager
class RecoveryExecutor:
    def execute(self, db, case: dict, policy_decision: str, action: str):
        if policy_decision != 'allow': return {'status': 'BLOCKED', 'result_details': {'reason': f'Policy: {policy_decision}'}}
        key = f"{case.get('payment_id', 'unknown')}_{action}_{uuid.uuid4().hex[:8]}"
        existing = idempotency_manager.check_and_record(db, key, action)
        if existing.status != 'PENDING': return {'status': existing.status, 'result_details': {}}
        result = {'status': 'SUCCESS', 'details': {'mode': 'RAZORPAY_TEST_MODE_SIMULATION', 'action': action}}
        existing.status = result['status']; existing.result_details = result.get('details', {}); db.commit()
        return result
executor = RecoveryExecutor()
