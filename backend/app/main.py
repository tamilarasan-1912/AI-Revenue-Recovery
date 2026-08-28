from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .api import webhooks, analytics, audit, simulation, review
from .config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title='RecoverAI API', version='1.2.4')

# The deployed frontend uses changing Vercel preview URLs. This API is
# simulation-only and does not use browser credentials, so a public CORS
# policy is appropriate for the demo API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(webhooks.router, prefix='/api/webhooks')
app.include_router(analytics.router, prefix='/api/analytics')
app.include_router(audit.router, prefix='/api/audit')
app.include_router(simulation.router, prefix='/api/simulation')
app.include_router(review.router, prefix='/api/review')

@app.get('/')
def read_root():
    return {
        'message': 'RecoverAI API is running',
        'status': 'healthy',
        'execution_mode': 'simulation',
        'version': '1.2.4'
    }
