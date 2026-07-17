"""Database engine and session factory.

All storage components obtain their SQLAlchemy session through ``get_session()``.
The database file lives at ``data/koach.db`` relative to the working directory
(i.e. the project root when the app is launched normally).

Usage:
    from f1_coach.infrastructure.storage.orm.database import init_db, get_session

    init_db()   # call once at application startup
    with get_session() as session:
        session.add(some_orm_object)
        session.commit()
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.orm.base import Base
from f1_coach.infrastructure.storage.orm import fsae_tables

logger = get_logger(__name__)

_DB_PATH = Path("data/koach.db")
_engine = None
_SessionFactory = None


def init_db() -> None:
    """Create the database file and all tables if they do not already exist.

    Safe to call multiple times — ``CREATE TABLE IF NOT EXISTS`` semantics.
    Must be called once before any repository is used.
    """
    global _engine, _SessionFactory

    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(
        f"sqlite:///{_DB_PATH}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    logger.info("Database initialised at %s", _DB_PATH.resolve())


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a transactional SQLAlchemy session.

    Commits on clean exit, rolls back on exception, always closes the session.

    Raises:
        RuntimeError: If ``init_db()`` has not been called yet.
    """
    if _SessionFactory is None:
        raise RuntimeError("Database not initialised — call init_db() at startup.")

    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
