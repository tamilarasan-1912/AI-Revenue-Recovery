from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = 'sqlite:///./recoverai.db'
    RAZORPAY_KEY_ID: str = ''
    RAZORPAY_KEY_SECRET: str = ''
    RAZORPAY_WEBHOOK_SECRET: str = ''
    ENABLE_RAZORPAY_TEST_ACTIONS: bool = False
    ALLOW_SQLITE_FALLBACK: bool = False
    REQUIRE_WEBHOOK_SIGNATURE: bool = True
    WEBHOOK_MAX_AGE_SECONDS: int = 300
    LLM_PROVIDER: str = 'deterministic'
    LLM_BASE_URL: str = ''
    LLM_API_KEY: str = ''
    LLM_MODEL: str = ''
    MAX_RETRIES: int = 3
    MIN_CONFIDENCE_THRESHOLD: float = 0.70
    INTERVENTION_COST: float = 5.0
    MAX_CUSTOMER_CONTACTS: int = 2
    RETRY_DELAYS_HOURS: str = '24,72,168'
    RESCUE_WINDOW_DAYS: int = 30
    ALLOWED_ACTIONS: list[str] = ['RETRY', 'PAYMENT_LINK', 'HUMAN_ESCALATION', 'STOP', 'WAIT']
    CORS_ORIGINS: str = '*'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == '*':
            return ['*']
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
        production_frontends = {
            'https://ai-revenue-recovery-nine.vercel.app',
            'https://frontend-bpkjb2id9-tamilarasan1.vercel.app',
            'https://frontend-bhoafqsmd-tamilarasan1.vercel.app',
        }
        origins.extend(origin for origin in production_frontends if origin not in origins)
        return origins

    def retry_delay_hours(self) -> tuple[int, ...]:
        try:
            values = tuple(max(1, int(x.strip())) for x in self.RETRY_DELAYS_HOURS.split(',') if x.strip())
            return values or (24, 72, 168)
        except ValueError:
            return (24, 72, 168)


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
