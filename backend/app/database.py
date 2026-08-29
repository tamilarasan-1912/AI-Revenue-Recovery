import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    url = settings.DATABASE_URL.strip()
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url


DATABASE_URL = _database_url()
_is_sqlite = DATABASE_URL.startswith('sqlite:')
_engine_kwargs = {'pool_pre_ping': True}
if _is_sqlite:
    _engine_kwargs['connect_args'] = {'check_same_thread': False}
else:
    _engine_kwargs['connect_args'] = {'connect_timeout': 5}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_fallback_engine = None
_FallbackSessionLocal = None


def _fallback_url() -> str:
    # Vercel/serverless filesystems are not persistent in the project folder;
    # /tmp is the writable location available to the function. Local/Docker
    # development keeps the fallback beside the backend process.
    if os.getenv('VERCEL'):
        return 'sqlite:////tmp/recoverai_fallback.db'
    return 'sqlite:///./recoverai_fallback.db'


def _get_fallback_sessionmaker():
    global _fallback_engine, _FallbackSessionLocal
    if _FallbackSessionLocal is None:
        _fallback_engine = create_engine(
            _fallback_url(),
            connect_args={'check_same_thread': False},
            pool_pre_ping=True,
        )
        Base.metadata.create_all(bind=_fallback_engine)
        _FallbackSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_fallback_engine)
    return _FallbackSessionLocal


def get_db():
    db = SessionLocal()
    try:
        db.execute(text('SELECT 1'))
        yield db
    except Exception:
        db.rollback()
        db.close()
        fallback_db = _get_fallback_sessionmaker()()
        try:
            yield fallback_db
        finally:
            fallback_db.close()
    else:
        db.close()
