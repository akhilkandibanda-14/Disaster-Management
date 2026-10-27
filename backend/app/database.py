"""SQLAlchemy database boundary with PostgreSQL/PostGIS support and lifecycle management."""

from collections.abc import Generator
from contextlib import contextmanager
import logging
from typing import Any, Dict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


# Build engine configuration based on dialect
engine_kwargs: Dict[str, Any] = {"pool_pre_ping": True}
if "sqlite" in settings.database_url:
    from sqlalchemy.pool import StaticPool
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["pool_size"] = settings.database_pool_size

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for request-scoped database sessions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        try:
            session.close()
        except Exception:
            pass


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for transactional database operations in background services and scripts.
    Automatically commits on success or rolls back on exception.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connectivity() -> dict:
    """Executes a lightweight query (SELECT 1) to verify database reachability without leaking secrets."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "dialect": engine.dialect.name,
            "target": settings.database_url.split("@")[-1] if "@" in settings.database_url else "configured",
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "dialect": engine.dialect.name,
            "error": f"Database connection failed: {type(e).__name__}",
        }


def verify_production_database_readiness() -> None:
    """Ensures that the application fails clearly upon startup if database is unreachable in production."""
    if settings.is_production():
        probe = check_db_connectivity()
        if probe["status"] != "connected":
            raise RuntimeError(
                f"FATAL: Production database is unreachable ({probe.get('error')}). "
                f"SafeMap AI requires an operational PostgreSQL instance in production."
            )


def database_target() -> str:
    """Returns database connection target with credentials masked."""
    if "@" in settings.database_url:
        return settings.database_url.split("@")[-1]
    return "local"
