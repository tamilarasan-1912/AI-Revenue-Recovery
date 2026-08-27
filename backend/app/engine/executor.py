from ..models import ActionType
from .idempotency import idempotency_manager


class RecoveryExecutor:
    """Execution boundary. This demo never moves real money."""

    def execute(self, db, case: dict, policy_decision: str, action: str, policy_decision_id: str = ""):
        if policy_decision != 'allow':
            return {'status': 'BLOCKED', 'result_details': {'reason': f'Policy: {policy_decision}'}}
        if action not in {a.value for a in ActionType}:
            return {'status': 'BLOCKED', 'result_details': {'reason': 'Unsupported action'}}

        key = idempotency_manager.make_key(case, action)
        existing = idempotency_manager.check_and_record(db, key, action, policy_decision_id)
        if existing is None:
            return {'status': 'ERROR', 'result_details': {'reason': 'Could not create execution record'}}
        if existing.status != 'PENDING':
            return {'status': existing.status, 'result_details': existing.result_details or {}, 'idempotent_replay': True}

        # Safe demo adapter: no real-money movement. The outcome is deterministic
        # and is replaced by a Razorpay Test Mode adapter when credentials are configured.
        amount = float(case.get('amount', 0) or 0)
        recoverable = case.get('is_recoverable')
        if action == ActionType.STOP.value:
            status = 'STOPPED'
        elif action == ActionType.HUMAN_ESCALATION.value:
            status = 'PENDING_HUMAN_REVIEW'
        elif recoverable is False:
            status = 'NO_RECOVERY'
        else:
            status = 'RECOVERED'

        details = {
            'mode': 'SIMULATION',
            'action': action,
            'amount': amount,
            'recovered_amount': amount if status == 'RECOVERED' else 0.0,
            'execution_boundary': 'No real-money movement',
        }
        existing.status = status
        existing.result_details = details
        db.commit()
        return {'status': status, 'result_details': details, 'idempotency_key': key}


executor = RecoveryExecutor()
