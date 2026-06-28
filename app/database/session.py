"""Database engine and session management."""

import logging
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def _get_engine():
    """Create and cache the database engine."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    database_url = settings.DATABASE_URL

    # Ensure data directory exists for SQLite
    if database_url.startswith("sqlite"):
        db_path = database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )

    # Enable WAL mode and foreign keys for SQLite
    if database_url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    logger.info("Database engine created: %s", database_url.split("?")[0])
    return _engine


def get_session_factory() -> sessionmaker:
    """Get the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Used for initial setup."""
    from app.database.base import Base
    # Import all models to register them with Base
    import app.models.user  # noqa: F401
    import app.models.work_entry  # noqa: F401
    import app.models.leave_type  # noqa: F401
    import app.models.settings  # noqa: F401
    import app.models.audit_log  # noqa: F401

    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
