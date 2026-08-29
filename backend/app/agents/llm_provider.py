"""AI decision boundary for RecoverAI.

The external LLM is optional. For uploaded datasets the local ML model supplies
recoverability evidence and the deterministic strategy layer converts that signal
into a recommendation. The model never receives execution authority.
"""
import json
import os
import urllib.request
from typing import Any


def _deterministic(prompt: str) -> dict[str, Any]:
    try:
        data = json.loads(prompt.split('|', 1)[1])
    except Exception:
        data = {}
    amount = float(data.get('amount', 0) or 0)
    reason = str(data.get('failure_reason', 'unknown')).lower()
    retries = int(data.get('retry_count', 0) or 0)
    ml_probability = data.get('ml_recoverability')

    if prompt.startswith('risk|'):
        if 'fraud' in reason:
            base = {'risk_score': 0.99, 'failure_class': 'fraud_suspected', 'confidence': 0.97}
        elif 'insufficient' in reason:
            base = {'risk_score': 0.72 if retries < 2 else 0.86, 'failure_class': 'insufficient_funds', 'confidence': 0.90}
        elif 'timeout' in reason or 'bank' in reason:
            base = {'risk_score': 0.82, 'failure_class': 'temporary_bank_degradation', 'confidence': 0.94}
        else:
            base = {'risk_score': 0.60, 'failure_class': 'unknown_payment_failure', 'confidence': 0.68}
        if ml_probability is not None:
            p = max(0.0, min(1.0, float(ml_probability)))
            base['risk_score'] = round(max(0.01, min(0.99, 1.0 - p)), 4)
            base['confidence'] = round(max(float(base['confidence']), abs(p - 0.5) * 2), 4)
        return {'revenue_at_risk': amount, **base}

    p = None if ml_probability is None else max(0.0, min(1.0, float(ml_probability)))
    risk_confidence = float(data.get('risk_confidence', 0.5) or 0.5)
    if 'fraud' in reason:
        action = 'STOP'
    elif retries >= 3:
        action = 'HUMAN_ESCALATION'
    elif p is not None and p < 0.30:
        action = 'STOP'
    elif p is not None and p < 0.65:
        action = 'HUMAN_ESCALATION'
    elif 'insufficient' in reason:
        action = 'PAYMENT_LINK'
    elif 'timeout' in reason or 'bank' in reason:
        action = 'RETRY' if retries < 2 else 'PAYMENT_LINK'
    else:
        action = 'PAYMENT_LINK'
    probability = p if p is not None else (0.80 if action in {'RETRY', 'PAYMENT_LINK'} else 0.35)
    confidence = max(0.50, min(0.99, max(risk_confidence, abs(probability - 0.5) * 2)))
    return {'recommended_action': action, 'expected_recovery_value': round(amount * probability, 2), 'confidence': round(confidence, 4)}


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
