from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    url = settings.DATABASE_URL.strip()
    # Some hosted Postgres providers still expose the legacy postgres:// form.
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url


DATABASE_URL = _database_url()
_is_sqlite = DATABASE_URL.startswith('sqlite:')
_engine_kwargs = {'pool_pre_ping': True}
if _is_sqlite:
    _engine_kwargs.update({'connect_args': {'check_same_thread': False}})

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# If a hosted Postgres instance is unavailable, the application can still boot
# and serve the demo using a local SQLite database. This prevents the entire
# dashboard from becoming HTTP 500/offline while a database service is being
# provisioned. A configured healthy Postgres database remains the primary DB.
_fallback_engine = None
_FallbackSessionLocal = None


def _get_fallback_sessionmaker():
    global _fallback_engine, _FallbackSessionLocal
    if _FallbackSessionLocal is None:
        _fallback_engine = create_engine(
            'sqlite:///./recoverai_fallback.db',
            connect_args={'check_same_thread': False},
            pool_pre_ping=True,
        )
        # Models are registered with Base.metadata during application import.
        Base.metadata.create_all(bind=_fallback_engine)
        _FallbackSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_fallback_engine)
    return _FallbackSessionLocal


def get_db():
    db = SessionLocal()
    try:
        # Force the connection now so a dead hosted DB does not surface later
        # as an opaque 500 from the endpoint query.
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
