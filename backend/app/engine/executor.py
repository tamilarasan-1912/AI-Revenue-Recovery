import base64
import json
import time
import urllib.request
import urllib.error
from ..config import settings
from ..models import ActionType, ExecutionRecord
from .idempotency import idempotency_manager


class RecoveryExecutor:
    """Bounded execution boundary. Real actions are allowed only in Razorpay Test Mode."""
    def _create_test_payment_link(self, case: dict) -> dict:
        if not settings.ENABLE_RAZORPAY_TEST_ACTIONS:
            return {'mode': 'SIMULATION', 'action': 'PAYMENT_LINK', 'execution_boundary': 'Razorpay Test Mode disabled; no external call made'}
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            return {'mode': 'SIMULATION', 'action': 'PAYMENT_LINK', 'execution_boundary': 'Test actions enabled but Razorpay credentials are missing'}
        if not settings.RAZORPAY_KEY_ID.startswith('rzp_test_'):
            return {'mode': 'BLOCKED', 'action': 'PAYMENT_LINK', 'execution_boundary': 'Live Razorpay keys are rejected by the buildathon safety boundary'}
        amount = int(round(float(case.get('amount', 0) or 0) * 100))
        if amount <= 0:
            return {'mode': 'BLOCKED', 'action': 'PAYMENT_LINK', 'execution_boundary': 'Invalid recovery amount'}
        reference_id = str(case.get('case_id') or case.get('payment_id') or 'recoverai')[:40]
        payload = {
            'amount': amount,
            'currency': 'INR',
            'accept_partial': False,
            'description': f"RecoverAI recovery for {case.get('payment_id', 'payment')}",
            'reference_id': reference_id,
            'expire_by': int(time.time()) + 30 * 24 * 60 * 60,
            'notify': {'sms': False, 'email': False},
        }
        customer = {}
        if case.get('customer_name'): customer['name'] = str(case['customer_name'])[:120]
        if case.get('customer_email'): customer['email'] = str(case['customer_email'])[:120]
        if case.get('customer_contact'): customer['contact'] = str(case['customer_contact'])[:20]
        if customer: payload['customer'] = customer
        token = base64.b64encode(f'{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}'.encode()).decode()
        request = urllib.request.Request('https://api.razorpay.com/v1/payment_links', data=json.dumps(payload).encode(), headers={'Authorization': f'Basic {token}', 'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = json.loads(response.read().decode())
            return {'mode': 'RAZORPAY_TEST_MODE', 'action': 'PAYMENT_LINK', 'payment_link_id': body.get('id'), 'short_url': body.get('short_url'), 'reference_id': reference_id, 'execution_boundary': 'Razorpay Test Mode only'}
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            return {'mode': 'RAZORPAY_TEST_MODE', 'action': 'PAYMENT_LINK', 'execution_boundary': 'External action failed safely', 'error': str(exc)}

    def execute(self, db, case: dict, policy_decision: str, action: str, policy_decision_id: str = ''):
        # A human reviewer approval is an explicit authorization transition.
        # It is not a new policy decision and must reuse the existing execution
        # record created while the case was awaiting review.
        if policy_decision == 'human_approved':
            policy_decision = 'allow'
        if policy_decision not in {'allow', 'human_review'}:
            return {'status': 'BLOCKED', 'result_details': {'reason': f'Policy: {policy_decision}'}}
        if action not in {a.value for a in ActionType}:
            return {'status': 'BLOCKED', 'result_details': {'reason': 'Unsupported action'}}

        existing = None
        execution_id = case.get('_execution_id')
        if execution_id:
            existing = db.query(ExecutionRecord).filter(ExecutionRecord.id == str(execution_id)).first()
            if existing is None:
                return {'status': 'ERROR', 'result_details': {'reason': 'Execution record no longer exists'}}
            if existing.action.value != action:
                return {'status': 'BLOCKED', 'result_details': {'reason': 'Execution action mismatch'}}
        else:
            key = idempotency_manager.make_key(case, action)
            existing = idempotency_manager.check_and_record(db, key, action, policy_decision_id)
            if existing is None:
                return {'status': 'ERROR', 'result_details': {'reason': 'Could not create execution record'}}

        if existing.status not in {'PENDING', 'PENDING_HUMAN_REVIEW'}:
            return {'status': existing.status, 'result_details': existing.result_details or {}, 'idempotent_replay': True, 'idempotency_key': existing.idempotency_key}
        if existing.status == 'PENDING_HUMAN_REVIEW' and policy_decision == 'allow':
            existing.status = 'PENDING'
            db.flush()

        if policy_decision == 'human_review' or action == ActionType.HUMAN_ESCALATION.value:
            if policy_decision == 'allow' and case.get('_human_approved'):
                status = 'HUMAN_REVIEW_APPROVED'
                details = {'mode': 'CONTROLLED_WORKFLOW', 'action': action, 'reason': 'Merchant approved the human-escalation decision'}
            else:
                status = 'PENDING_HUMAN_REVIEW'
                details = {'mode': 'CONTROLLED_WORKFLOW', 'action': action, 'reason': 'Policy requires compliant human escalation'}
        elif action == ActionType.STOP.value:
            status = 'STOPPED'
            details = {'mode': 'CONTROLLED_WORKFLOW', 'action': action, 'reason': 'Recovery stopped by policy'}
        elif action == ActionType.WAIT.value:
            status = 'WAITING'
            details = {'mode': 'CONTROLLED_WORKFLOW', 'action': action, 'reason': 'Recovery deferred by policy'}
        elif action == ActionType.PAYMENT_LINK.value:
            details = self._create_test_payment_link(case)
            status = 'RECOVERY_LINK_CREATED' if details.get('short_url') else 'RECOVERY_ACTION_READY'
        elif case.get('is_recoverable') is False:
            status = 'NO_RECOVERY'
            details = {'mode': 'SIMULATION', 'action': action, 'reason': 'Uploaded dataset ground truth marks this row non-recoverable'}
        else:
            status = 'RECOVERED'
            details = {'mode': 'SIMULATION', 'action': action, 'amount': float(case.get('amount', 0) or 0), 'recovered_amount': float(case.get('amount', 0) or 0), 'execution_boundary': 'No real-money movement'}

        existing.status = status
        existing.result_details = {**(existing.result_details or {}), **details}
        db.commit()
        return {'status': status, 'result_details': existing.result_details, 'idempotency_key': existing.idempotency_key}


executor = RecoveryExecutor()
