from ..config import settings
from ..models import PolicyDecisionEnum, ActionType
class PolicyEngine:
    def evaluate(self, case: dict):
        rules = []
        action = case.get('recommended_action')
        confidence = case.get('ai_confidence', 0.0)
        retry_count = case.get('retry_count', 0)
        expected_value = case.get('expected_recovery_value', 0.0)
        fraud = case.get('fraud_signal', False)
        decision = PolicyDecisionEnum.ALLOW
        if action not in settings.ALLOWED_ACTIONS: decision = PolicyDecisionEnum.BLOCK; rules.append('ACTION_NOT_ALLOWED')
        elif action == ActionType.RETRY.value and retry_count >= settings.MAX_RETRIES: decision = PolicyDecisionEnum.STOP; rules.append('MAX_RETRIES_EXCEEDED')
        elif confidence < settings.MIN_CONFIDENCE_THRESHOLD: decision = PolicyDecisionEnum.HUMAN_REVIEW; rules.append('LOW_CONFIDENCE')
        elif fraud: decision = PolicyDecisionEnum.STOP; rules.append('FRAUD_SIGNAL')
        elif expected_value < settings.INTERVENTION_COST and action == ActionType.PAYMENT_LINK.value: decision = PolicyDecisionEnum.STOP; rules.append('ECONOMIC_THRESHOLD_NOT_MET')
        return {'decision': decision.value, 'policy_version': 'v1.0', 'rules_triggered': rules}
policy_engine = PolicyEngine()
