"""AI decision boundary for RecoverAI.

The external LLM is optional. The uploaded-data ML model supplies learned
recoverability evidence, while the research-backed recovery playbook converts
that evidence and payment-failure context into a safe next-best action.
The model never receives execution authority.
"""
import json
import os
import urllib.request
from typing import Any

from ..recovery_playbook import build_recovery_plan


def _deterministic(prompt: str) -> dict[str, Any]:
    try:
        data = json.loads(prompt.split('|', 1)[1])
    except Exception:
        data = {}

    amount = float(data.get('amount', 0) or 0)
    reason = str(data.get('failure_reason', 'unknown')).lower()
    retries = int(data.get('retry_count', 0) or 0)
    ml_probability = data.get('ml_recoverability')
    p = None if ml_probability is None else max(0.0, min(1.0, float(ml_probability)))

    if prompt.startswith('risk|'):
        decline_code = str(data.get('decline_code', '') or '').lower()
        if 'fraud' in reason or 'fraud' in decline_code:
            base = {'risk_score': 0.99, 'failure_class': 'fraud_suspected', 'confidence': 0.97}
        elif any(token in reason for token in ('insufficient', 'balance')) or decline_code == '51':
            base = {'risk_score': 0.72 if retries < 2 else 0.86, 'failure_class': 'insufficient_funds', 'confidence': 0.90}
        elif any(token in reason for token in ('timeout', 'gateway', 'network', 'unavailable', 'temporary')):
            base = {'risk_score': 0.82, 'failure_class': 'temporary_bank_degradation', 'confidence': 0.94}
        elif any(token in reason for token in ('expired', 'closed', 'blocked', 'stolen', 'invalid')):
            base = {'risk_score': 0.88, 'failure_class': 'payment_instrument_problem', 'confidence': 0.92}
        elif any(token in reason for token in ('authentication', 'otp', '3ds')):
            base = {'risk_score': 0.55, 'failure_class': 'authentication_required', 'confidence': 0.90}
        else:
            base = {'risk_score': 0.60, 'failure_class': 'unknown_payment_failure', 'confidence': 0.68}
        if p is not None:
            base['risk_score'] = round(max(0.01, min(0.99, 1.0 - p)), 4)
            base['confidence'] = round(max(float(base['confidence']), abs(p - 0.5) * 2), 4)
        return {'revenue_at_risk': amount, **base}

    risk_confidence = float(data.get('risk_confidence', 0.5) or 0.5)
    plan = build_recovery_plan(data)
    action = plan['recommended_action']

    if reason == 'insufficient_funds':
        action = 'PAYMENT_LINK'
    elif p is not None and action == 'RETRY' and p < 0.65:
        plan = build_recovery_plan({**data, 'ml_recoverability': p})
        action = plan['recommended_action']

    if action == 'STOP':
        confidence = 0.99
    elif action == 'RETRY':
        confidence = max(0.70, p if p is not None else 0.80)
    elif action == 'PAYMENT_LINK':
        confidence = max(0.75, 1.0 - p if p is not None else 0.80)
    else:
        confidence = max(0.70, min(0.99, max(risk_confidence, 1.0 - abs((p or 0.5) - 0.5) * 0.5)))

    probability = p if p is not None else (0.80 if action in {'RETRY', 'PAYMENT_LINK'} else 0.35)
    return {
        'recommended_action': action,
        'expected_recovery_value': round(amount * probability, 2) if action != 'STOP' else 0.0,
        'confidence': round(min(0.99, confidence), 4),
        'recovery_plan': plan,
    }


def _external_openai_compatible(prompt: str) -> dict[str, Any] | None:
    endpoint = os.getenv('LLM_BASE_URL', '').rstrip('/')
    api_key = os.getenv('LLM_API_KEY', '')
    model = os.getenv('LLM_MODEL', '')
    if not endpoint or not api_key or not model:
        return None
    body = json.dumps({'model': model, 'messages': [{'role': 'system', 'content': 'Return only valid JSON. Never execute financial actions.'}, {'role': 'user', 'content': prompt}], 'temperature': 0, 'response_format': {'type': 'json_object'}}).encode()
    request = urllib.request.Request(endpoint + '/chat/completions', data=body, headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode())
    return json.loads(payload['choices'][0]['message']['content'])


class RecoveryLLMProvider:
    def generate_structured(self, prompt: str, schema: dict, use_external: bool = True) -> dict[str, Any]:
        result = None
        if use_external and os.getenv('LLM_PROVIDER', 'deterministic') == 'openai_compatible':
            try:
                result = _external_openai_compatible(prompt)
            except Exception:
                result = None
        if result is None:
            result = _deterministic(prompt)
        if not isinstance(result, dict):
            raise ValueError('AI response must be an object')
        return result


def get_llm_provider() -> RecoveryLLMProvider:
    return RecoveryLLMProvider()


llm_provider = get_llm_provider()
