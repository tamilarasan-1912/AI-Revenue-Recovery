from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .api import webhooks, analytics, audit, simulation, review, failure_injection, system, payments

Base.metadata.create_all(bind=engine)

app = FastAPI(title='RecoverAI API', version='1.3.0')

# Vercel creates a new preview hostname for many deployments. The previous
# configuration depended on a small hard-coded list, so a new preview could
# reach the healthy Render API but still be rejected by the browser's CORS
# policy. Keep the configured origins and additionally allow this project's
# Vercel preview/deployment hostnames.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_origin_regex=r'^https://[a-zA-Z0-9.-]+\.vercel\.app$',
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['*'],
)

app.include_router(webhooks.router, prefix='/api/webhooks')
app.include_router(analytics.router, prefix='/api/analytics')
app.include_router(audit.router, prefix='/api/audit')
app.include_router(simulation.router, prefix='/api/simulation')
app.include_router(review.router, prefix='/api/review')
app.include_router(failure_injection.router, prefix='/api/failure-injection')
app.include_router(system.router, prefix='/api/system')
app.include_router(payments.router, prefix='/api/payments')


@app.get('/')
def read_root():
    return {
        'message': 'RecoverAI API is running',
        'status': 'healthy',
        'execution_mode': 'razorpay_test_mode' if settings.ENABLE_RAZORPAY_TEST_ACTIONS else 'simulation',
        'version': '1.3.0',
    }
