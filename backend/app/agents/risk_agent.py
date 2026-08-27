from .llm_provider import llm_provider
def analyze_risk(payment_data: dict):
    result = llm_provider.generate_structured(f"risk {payment_data.get('amount')}", {})
    result['fraud_signal'] = result.get('failure_class') == 'fraud_suspected'
    return result
