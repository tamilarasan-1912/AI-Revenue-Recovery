from pydantic_settings import BaseSettings
from functools import lru_cache
class Settings(BaseSettings):
    DATABASE_URL: str = 'postgresql://postgres:postgres@localhost:5432/recoverai'
    RAZORPAY_WEBHOOK_SECRET: str = ''
    LLM_PROVIDER: str = 'mock'
    MAX_RETRIES: int = 3
    MIN_CONFIDENCE_THRESHOLD: float = 0.70
    INTERVENTION_COST: float = 5.0
    ALLOWED_ACTIONS: list = ['RETRY', 'PAYMENT_LINK', 'HUMAN_ESCALATION', 'STOP', 'WAIT']
    class Config: env_file = '.env'
@lru_cache()
def get_settings(): return Settings()
settings = get_settings()
