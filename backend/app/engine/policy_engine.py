from ..config import settings
from ..models import PolicyDecisionEnum, ActionType


class PolicyEngine:
    """Deterministic safety gate. AI can recommend; only policy can authorize execution."""

    def evaluate(self, case: dict):
        rules = []
        action = case.get('recommended_action')
        confidence = float(case.get('ai_confidence', 0.0) or 0.0)
        retry_count = int(case.get('retry_count', 0) or 0)
        expected_value = float(case.get('expected_recovery_value', 0.0) or 0.0)
        fraud = bool(case.get('fraud_signal', False))
        decision = PolicyDecisionEnum.ALLOW

        if action not in settings.ALLOWED_ACTIONS:
            decision = PolicyDecisionEnum.BLOCK
            rules.append('ACTION_NOT_ALLOWED')
        elif fraud:
            decision = PolicyDecisionEnum.STOP
            rules.append('FRAUD_SIGNAL')
        elif action == ActionType.HUMAN_ESCALATION.value:
            decision = PolicyDecisionEnum.HUMAN_REVIEW
            rules.append('EXPLICIT_HUMAN_ESCALATION')
        elif action == ActionType.RETRY.value and retry_count >= settings.MAX_RETRIES:
            decision = PolicyDecisionEnum.STOP
            rules.append('MAX_RETRIES_EXCEEDED')
        elif action == ActionType.WAIT.value:
            decision = PolicyDecisionEnum.HUMAN_REVIEW
            rules.append('WAIT_FOR_LATER_RETRY_WINDOW')
        elif confidence < settings.MIN_CONFIDENCE_THRESHOLD:
            decision = PolicyDecisionEnum.HUMAN_REVIEW
            rules.append('LOW_CONFIDENCE')
        elif action in {ActionType.PAYMENT_LINK.value, ActionType.RETRY.value} and expected_value < settings.INTERVENTION_COST:
            decision = PolicyDecisionEnum.STOP
            rules.append('ECONOMIC_THRESHOLD_NOT_MET')
        elif action == ActionType.STOP.value:
            decision = PolicyDecisionEnum.STOP
            rules.append('MODEL_REQUESTED_STOP')

        return {
            'decision': decision.value,
            'policy_version': 'v1.3',
            'rules_triggered': rules,
        }


policy_engine = PolicyEngine()
