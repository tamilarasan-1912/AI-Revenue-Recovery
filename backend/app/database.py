from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings
from .runtime_dataset import get_dataset


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
_demo_engine = None
_DemoSessionLocal = None


def _get_fallback_sessionmaker():
    """Explicit persistent local-demo fallback; never silently replaces production Postgres."""
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


def _get_demo_sessionmaker():
    """Process-local SQLite used only for an uploaded-CSV demo when Postgres is unavailable."""
    global _demo_engine, _DemoSessionLocal
    if _DemoSessionLocal is None:
        _demo_engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            pool_pre_ping=True,
        )
        Base.metadata.create_all(bind=_demo_engine)
        _DemoSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_demo_engine)
    return _DemoSessionLocal


def get_db():
    db = SessionLocal()
    try:
        db.execute(text('SELECT 1'))
        yield db
    except Exception as exc:
        db.rollback()
        db.close()
        batch_id, rows = get_dataset()
        if rows:
            demo_db = _get_demo_sessionmaker()()
            try:
                yield demo_db
            finally:
                demo_db.close()
            return
        if not settings.ALLOW_SQLITE_FALLBACK:
            raise HTTPException(status_code=503, detail='Primary database is unavailable') from exc
        fallback_db = _get_fallback_sessionmaker()()
        try:
            yield fallback_db
        finally:
            fallback_db.close()
    else:
        db.close()
