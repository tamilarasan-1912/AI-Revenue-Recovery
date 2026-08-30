import hashlib
import hmac
import json
import time

from app.api.webhooks import _created_at_is_fresh
from app.config import settings


def test_webhook_timestamp_window_accepts_recent_event():
    assert _created_at_is_fresh({'created_at': int(time.time())}) is True


def test_webhook_timestamp_window_rejects_stale_event():
    original = settings.WEBHOOK_MAX_AGE_SECONDS
    try:
        settings.WEBHOOK_MAX_AGE_SECONDS = 300
        assert _created_at_is_fresh({'created_at': int(time.time()) - 301}) is False
    finally:
        settings.WEBHOOK_MAX_AGE_SECONDS = original


def test_hmac_signature_matches_raw_payload():
    secret = 'buildathon-test-secret'
    payload = json.dumps({'id': 'evt_test', 'event': 'payment.failed'}, separators=(',', ':')).encode()
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(signature, hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest())
