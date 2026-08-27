from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = 'postgresql://postgres:postgres@localhost:5432/recoverai'
    RAZORPAY_KEY_ID: str = ''
    RAZORPAY_KEY_SECRET: str = ''
    RAZORPAY_WEBHOOK_SECRET: str = ''
    LLM_PROVIDER: str = 'deterministic'
    LLM_BASE_URL: str = ''
    LLM_API_KEY: str = ''
    LLM_MODEL: str = ''
    MAX_RETRIES: int = 3
    MIN_CONFIDENCE_THRESHOLD: float = 0.70
    INTERVENTION_COST: float = 5.0
    MAX_CUSTOMER_CONTACTS: int = 2
    ALLOWED_ACTIONS: list[str] = ['RETRY', 'PAYMENT_LINK', 'HUMAN_ESCALATION', 'STOP', 'WAIT']
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
