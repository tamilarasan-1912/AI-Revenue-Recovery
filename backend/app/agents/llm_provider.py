class MockLLMProvider:
    def generate_structured(self, prompt: str, schema: dict):
        if 'risk' in prompt.lower(): return {'revenue_at_risk': 4999.0, 'risk_score': 0.82, 'failure_class': 'temporary_bank_degradation', 'confidence': 0.93}
        if 'strategy' in prompt.lower(): return {'recommended_action': 'PAYMENT_LINK', 'expected_recovery_value': 4200.0, 'confidence': 0.91}
        return {}
def get_llm_provider(): return MockLLMProvider()
llm_provider = get_llm_provider()
