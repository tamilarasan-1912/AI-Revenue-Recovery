from fastapi import HTTPException
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


def _get_fallback_sessionmaker():
    """Explicit local-demo fallback; never silently replace production Postgres."""
    global _fallback_engine, _FallbackSessionLocal
    if not settings.ALLOW_SQLITE_FALLBACK:
        raise RuntimeError('Primary database is unavailable and ALLOW_SQLITE_FALLBACK is disabled')
    if _FallbackSessionLocal is None:
        _fallback_engine = create_engine(
            'sqlite:///./recoverai_fallback.db',
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
    except Exception as exc:
        db.rollback()
        db.close()
        if not settings.ALLOW_SQLITE_FALLBACK:
            raise HTTPException(status_code=503, detail='Primary database is unavailable') from exc
        fallback_db = _get_fallback_sessionmaker()()
        try:
            yield fallback_db
        finally:
            fallback_db.close()
    else:
        db.close()
