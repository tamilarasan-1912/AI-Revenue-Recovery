from fastapi import APIRouter
from ..recovery_playbook import build_recovery_plan
from ..config import settings

router = APIRouter()


@router.post('/plan')
def recovery_plan(payload: dict):
    """Explain the safest recovery sequence for one failed payment."""
    return build_recovery_plan(
        payload,
        max_retries=settings.MAX_RETRIES,
        retry_delays_hours=settings.retry_delay_hours(),
        rescue_window_days=settings.RESCUE_WINDOW_DAYS,
    )


@router.get('/policy')
def recovery_policy():
    return {
        'max_retries': settings.MAX_RETRIES,
        'retry_delays_hours': settings.retry_delay_hours(),
        'rescue_window_days': settings.RESCUE_WINDOW_DAYS,
        'principles': [
            'Retry only failures classified as potentially temporary.',
            'Do not repeatedly retry fraud or hard declines.',
            'Use customer action/payment-link recovery when the instrument needs updating.',
            'Keep retries bounded and idempotent.',
            'Escalate ambiguous or low-confidence cases to a human.',
        ],
    }
