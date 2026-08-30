import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from .config import settings
from .database import engine, Base
from .api import webhooks, analytics, audit, simulation, review, failure_injection, system, payments, recovery

logger = logging.getLogger(__name__)

try:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if inspector.has_table('imported_dataset_rows') and 'features' not in {c['name'] for c in inspector.get_columns('imported_dataset_rows')}:
        with engine.begin() as conn:
            if engine.dialect.name == 'postgresql':
                conn.execute(text('ALTER TABLE imported_dataset_rows ADD COLUMN IF NOT EXISTS features JSONB'))
            else:
                conn.execute(text('ALTER TABLE imported_dataset_rows ADD COLUMN features JSON'))
except Exception:
    # Keep the process bootable so the readiness endpoint can expose the real
    # database failure. Production never silently switches to another store.
    logger.exception('Database initialization failed; API will report degraded readiness')

app = FastAPI(title='RecoverAI API', version='1.5.0')

# The deployed frontend is hosted on Render. Keep an explicit allow-list from
# configuration, and also allow the app's Render/Vercel deployment origins so
# a stale CORS_ORIGINS environment variable cannot break the browser demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_origin_regex=r'^https://[a-zA-Z0-9.-]+\.(?:onrender\.com|vercel\.app)$',
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['*'],
)

app.include_router(webhooks.router, prefix='/api/webhooks')
app.include_router(analytics.router, prefix='/api/analytics')
app.include_router(audit.router, prefix='/api/audit')
app.include_router(simulation.router, prefix='/api/simulation')
app.include_router(review.router, prefix='/api/review')
app.include_router(recovery.router, prefix='/api/recovery')
app.include_router(failure_injection.router, prefix='/api/failure-injection')
app.include_router(system.router, prefix='/api/system')
app.include_router(payments.router, prefix='/api/payments')


@app.get('/')
def read_root():
    return {
        'message': 'RecoverAI API is running',
        'status': 'healthy',
        'execution_mode': 'razorpay_test_mode' if settings.ENABLE_RAZORPAY_TEST_ACTIONS else 'simulation',
        'version': '1.5.0',
    }
