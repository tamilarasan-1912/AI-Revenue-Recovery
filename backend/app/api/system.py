import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db

router = APIRouter()

APP_VERSION = '1.5.1'


def _build_info() -> dict[str, str]:
    return {
        'version': APP_VERSION,
        'git_commit': os.getenv('RENDER_GIT_COMMIT', 'local')[:40],
        'git_branch': os.getenv('RENDER_GIT_BRANCH', 'local'),
    }


@router.get('/live')
def liveness():
    """Cheap process liveness probe for Render.

    This endpoint intentionally does not touch Postgres. Render health checks must
    not depend on a slow/unavailable external dependency, otherwise a healthy
    application process can be removed from traffic before the database recovers.
    """
    return {'status': 'alive', **_build_info()}


@router.get('/health')
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text('SELECT 1'))
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Database is not ready') from exc
    return {
        'status': 'healthy',
        'database': 'ok',
        'execution_mode': 'razorpay_test_mode' if settings.ENABLE_RAZORPAY_TEST_ACTIONS else 'simulation',
        'test_keys_configured': bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
        'webhook_signature_configured': bool(settings.RAZORPAY_WEBHOOK_SECRET),
        'webhook_signature_required': settings.REQUIRE_WEBHOOK_SIGNATURE,
        'llm_provider': settings.LLM_PROVIDER,
        'sqlite_fallback_enabled': settings.ALLOW_SQLITE_FALLBACK,
        **_build_info(),
    }


@router.get('/policies')
def policies():
    return {
        'policy_version': 'v1.5',
        'max_retries': settings.MAX_RETRIES,
        'min_confidence_threshold': settings.MIN_CONFIDENCE_THRESHOLD,
        'intervention_cost': settings.INTERVENTION_COST,
        'max_customer_contacts': settings.MAX_CUSTOMER_CONTACTS,
        'allowed_actions': settings.ALLOWED_ACTIONS,
        'rules': [
            {'id': 'FRAUD_SIGNAL', 'effect': 'STOP', 'description': 'Fraud signals override recovery recommendations.'},
            {'id': 'MAX_RETRIES_EXCEEDED', 'effect': 'STOP', 'description': 'Retry is stopped after the configured retry budget.'},
            {'id': 'LOW_CONFIDENCE', 'effect': 'HUMAN_REVIEW', 'description': 'Low-confidence recommendations require merchant approval.'},
            {'id': 'ECONOMIC_THRESHOLD_NOT_MET', 'effect': 'STOP', 'description': 'Interventions below the configured economic threshold are not executed.'},
            {'id': 'ACTION_NOT_ALLOWED', 'effect': 'BLOCK', 'description': 'Unknown actions can never reach the executor.'},
            {'id': 'WAIT_FOR_LATER_RETRY_WINDOW', 'effect': 'HUMAN_REVIEW', 'description': 'Deferred recovery is not treated as an immediate money action.'},
        ],
    }
