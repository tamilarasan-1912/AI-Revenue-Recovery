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
    _engine_kwargs['connect_args'] = {'check_same_thread': False, 'timeout': 30}
else:
    _engine_kwargs['connect_args'] = {'connect_timeout': 5}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_fallback_engine = None
_FallbackSessionLocal = None
_demo_engine = None
_DemoSessionLocal = None


# Additive migrations required because SQLAlchemy create_all() does not alter
# existing production tables. These are all nullable/simple columns, so the
# migration is safe for existing rows and can run on every deployment.
_ADDITIVE_COLUMNS = {
    'executions': {
        'reviewed_by': ('TEXT', 'VARCHAR'),
        'reviewed_at': ('DATETIME', 'TIMESTAMPTZ'),
        'review_decision': ('TEXT', 'VARCHAR'),
    },
    'imported_dataset_rows': {
        'features': ('JSON', 'JSONB'),
    },
}


def _ensure_schema(target_engine):
    """Create tables and apply all known additive schema migrations."""
    Base.metadata.create_all(bind=target_engine)
    inspector = inspect(target_engine)

    for table_name, columns in _ADDITIVE_COLUMNS.items():
        if not inspector.has_table(table_name):
            continue
        existing = {column['name'] for column in inspector.get_columns(table_name)}
        for column_name, (sqlite_type, postgres_type) in columns.items():
            if column_name in existing:
                continue
            dialect = target_engine.dialect.name
            column_type = postgres_type if dialect == 'postgresql' else sqlite_type
            try:
                with target_engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'))
            except Exception as exc:
                # Multiple Render workers can race during first startup. If a
                # different worker added the column between inspection and ALTER,
                # treat that as success and continue; all other migration errors
                # must still surface so database routing can fail over safely.
                message = str(exc).lower()
                if 'duplicate column' not in message and 'already exists' not in message:
                    raise
            inspector = inspect(target_engine)


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
            connect_args={'check_same_thread': False, 'timeout': 30},
            pool_pre_ping=True,
        )
        _ensure_schema(_fallback_engine)
        _FallbackSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_fallback_engine)
    return _FallbackSessionLocal


def _get_demo_sessionmaker():
    """Persistent local SQLite used for uploaded-CSV demos when Postgres is unavailable."""
    global _demo_engine, _DemoSessionLocal
    if _DemoSessionLocal is None:
        _demo_engine = create_engine(
            'sqlite:///./recoverai_demo.db',
            connect_args={'check_same_thread': False, 'timeout': 30},
            pool_pre_ping=True,
        )
        _ensure_schema(_demo_engine)
        _DemoSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_demo_engine)
    return _DemoSessionLocal


def _demo_has_dataset() -> bool:
    """Return whether the persistent demo store contains an uploaded cohort."""
    try:
        DemoSession = _get_demo_sessionmaker()
        session = DemoSession()
        try:
            from .models import ImportedDatasetRow
            return session.query(ImportedDatasetRow.id).first() is not None
        finally:
            session.close()
    except Exception:
        return False


def _primary_has_dataset(db) -> bool:
    try:
        from .models import ImportedDatasetRow
        return db.query(ImportedDatasetRow.id).first() is not None
    except Exception:
        return False


def get_db(request: Request):
    """Yield a healthy database session, recovering gracefully from outages.

    If Postgres is healthy but an earlier upload was written to the demo store
    during an outage, keep using the demo store until the primary has its own
    uploaded cohort. This prevents an outage/recovery transition from making the
    dataset mysteriously disappear between pages.
    """
    db = SessionLocal()
    try:
        db.execute(text('SELECT 1'))
        _ensure_schema(engine)

        # Dataset import should always target the primary when it is available.
        # For read/evaluation routes, prefer an existing demo cohort if primary is
        # empty. This makes recovery from a temporary Postgres outage seamless.
        if not request.url.path.endswith('/simulation/import-dataset') and not _primary_has_dataset(db) and _demo_has_dataset():
            db.close()
            DemoSession = _get_demo_sessionmaker()
            demo_db = DemoSession()
            try:
                yield demo_db
            finally:
                demo_db.close()
            return

        yield db
    except HTTPException:
        db.close()
        raise
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass

        if settings.ALLOW_SQLITE_FALLBACK:
            fallback_db = _get_fallback_sessionmaker()()
            try:
                yield fallback_db
            finally:
                fallback_db.close()
            return

        # Uploaded-dataset routes can operate from the persistent demo store when
        # the primary database is unavailable. This is intentionally limited to
        # dataset/demo operation rather than silently hiding production DB errors.
        if request.url.path.endswith('/simulation/import-dataset') or _demo_has_dataset() or get_dataset()[1]:
            demo_db = _get_demo_sessionmaker()()
            try:
                yield demo_db
            finally:
                demo_db.close()
            return

        raise HTTPException(status_code=503, detail='Primary database is unavailable') from exc
