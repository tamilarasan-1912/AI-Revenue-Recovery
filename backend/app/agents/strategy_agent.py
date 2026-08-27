from .llm_provider import llm_provider
def recommend_strategy(payment_data: dict, risk_analysis: dict):
    return llm_provider.generate_structured(f"strategy {risk_analysis.get('failure_class')}", {})
