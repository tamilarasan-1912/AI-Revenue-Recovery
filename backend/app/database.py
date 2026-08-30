from fastapi import HTTPException, Request
from sqlalchemy import create_engine, inspect, text
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


def _ensure_schema(target_engine):
    """Create tables and apply small additive migrations to every database path.

    create_all() does not alter existing tables. The uploaded-dataset model gained
    the optional `features` column after some demo SQLite files had already been
    created, so every primary/fallback/demo engine must run the same migration.
    """
    Base.metadata.create_all(bind=target_engine)
    try:
        inspector = inspect(target_engine)
        if inspector.has_table('imported_dataset_rows'):
            columns = {column['name'] for column in inspector.get_columns('imported_dataset_rows')}
            if 'features' not in columns:
                with target_engine.begin() as conn:
                    if target_engine.dialect.name == 'postgresql':
                        conn.execute(text('ALTER TABLE imported_dataset_rows ADD COLUMN IF NOT EXISTS features JSONB'))
                    elif target_engine.dialect.name == 'sqlite':
                        conn.execute(text('ALTER TABLE imported_dataset_rows ADD COLUMN features JSON'))
                    else:
                        conn.execute(text('ALTER TABLE imported_dataset_rows ADD COLUMN features JSON'))
    except Exception:
        # Schema creation/migration is retried on the next request; do not hide
        # the original database availability decision made by get_db().
        raise


def initialize_primary_schema():
    """Best-effort startup initialization for the configured primary database."""
    _ensure_schema(engine)


def _get_fallback_sessionmaker():
    """Persistent local fallback used when explicitly enabled for demo/degraded deployments."""
    global _fallback_engine, _FallbackSessionLocal
    if not settings.ALLOW_SQLITE_FALLBACK:
        raise RuntimeError('Primary database is unavailable and ALLOW_SQLITE_FALLBACK is disabled')
    if _FallbackSessionLocal is None:
        _fallback_engine = create_engine(
            'sqlite:///./recoverai_fallback.db',
            connect_args={'check_same_thread': False},
            pool_pre_ping=True,
        )
        _ensure_schema(_fallback_engine)
        _FallbackSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_fallback_engine)
    return _FallbackSessionLocal


def _get_demo_sessionmaker():
    """Persistent local SQLite used for uploaded-CSV demos when Postgres is unavailable.

    This intentionally uses a file rather than in-memory SQLite so multiple
    Render worker processes can observe the same uploaded dataset during a demo.
    The real Postgres path is unchanged and remains the production source of truth.
    """
    global _demo_engine, _DemoSessionLocal
    if _DemoSessionLocal is None:
        _demo_engine = create_engine(
            'sqlite:///./recoverai_demo.db',
            connect_args={'check_same_thread': False},
            pool_pre_ping=True,
        )
        _ensure_schema(_demo_engine)
        _DemoSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_demo_engine)
    return _DemoSessionLocal


def _demo_has_dataset() -> bool:
    if _DemoSessionLocal is None:
        return False
    try:
        from .models import ImportedDatasetRow
        session = _DemoSessionLocal()
        try:
            return session.query(ImportedDatasetRow.id).first() is not None
        finally:
            session.close()
    except Exception:
        return False


def get_db(request: Request):
    db = SessionLocal()
    try:
        db.execute(text('SELECT 1'))
        yield db
    except Exception as exc:
        db.rollback()
        db.close()

        if settings.ALLOW_SQLITE_FALLBACK:
            fallback_db = _get_fallback_sessionmaker()()
            try:
                yield fallback_db
            finally:
                fallback_db.close()
            return

        if request.url.path.endswith('/simulation/import-dataset') or _demo_has_dataset() or get_dataset()[1]:
            demo_db = _get_demo_sessionmaker()()
            try:
                yield demo_db
            finally:
                demo_db.close()
            return

        raise HTTPException(status_code=503, detail='Primary database is unavailable') from exc
    else:
        db.close()
