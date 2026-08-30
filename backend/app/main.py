import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    logger.exception('Database initialization failed; API will report degraded readiness')

app = FastAPI(title='RecoverAI API', version='1.5.0')

# Keep the deployment origins explicit and also support Render/Vercel preview
# deployments. The exception handler below ensures CORS headers are still
# present when an endpoint raises an unexpected 500.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_origin_regex=r'^https://[a-zA-Z0-9.-]+\.(?:onrender\.com|vercel\.app)$',
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['*'],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception('Unhandled API error on %s %s', request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal server error', 'error_type': exc.__class__.__name__},
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
