from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = 'postgresql://postgres:postgres@localhost:5432/recoverai'
    RAZORPAY_KEY_ID: str = ''
    RAZORPAY_KEY_SECRET: str = ''
    RAZORPAY_WEBHOOK_SECRET: str = ''
    ENABLE_RAZORPAY_TEST_ACTIONS: bool = False
    LLM_PROVIDER: str = 'deterministic'
    LLM_BASE_URL: str = ''
    LLM_API_KEY: str = ''
    LLM_MODEL: str = ''
    MAX_RETRIES: int = 3
    MIN_CONFIDENCE_THRESHOLD: float = 0.70
    INTERVENTION_COST: float = 5.0
    MAX_CUSTOMER_CONTACTS: int = 2
    ALLOWED_ACTIONS: list[str] = ['RETRY', 'PAYMENT_LINK', 'HUMAN_ESCALATION', 'STOP', 'WAIT']
    CORS_ORIGINS: str = '*'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == '*':
            return ['*']
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
        production_frontend = 'https://ai-revenue-recovery-nine.vercel.app'
        if production_frontend not in origins:
            origins.append(production_frontend)
        return origins


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
