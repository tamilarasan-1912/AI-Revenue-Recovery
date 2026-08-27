from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .api import webhooks, analytics, audit
Base.metadata.create_all(bind=engine)
app = FastAPI(title='RecoverAI API')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
app.include_router(webhooks.router, prefix='/api/webhooks')
app.include_router(analytics.router, prefix='/api/analytics')
app.include_router(audit.router, prefix='/api/audit')
@app.get('/')
def read_root(): return {'message': 'RecoverAI API is running', 'status': 'healthy'}
