"""SQLite implementation of SessionRepository.

This class satisfies the SessionRepository Protocol defined in domain/ports.
It is injected into application services at startup — the domain layer never
imports this file directly.
"""

from sqlalchemy.orm import joinedload

from f1_coach.domain.models.session import Session
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.mappers.domain_mapper import (
    session_to_domain,
    session_to_orm,
)
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.tables import SessionORM

logger = get_logger(__name__)


class SQLiteSessionRepository:
    """Persists and retrieves Session aggregates using SQLite via SQLAlchemy."""

    def save(self, session: Session) -> None:
        """Insert a new session or update an existing one.

        Sets ``session.id`` after a successful insert.
        """
        with get_session() as db:
            if session.is_persisted:
                orm = db.get(SessionORM, session.id)
                if orm is None:
                    raise ValueError(f"Session id={session.id} not found in database.")
                orm.session_uid = session.session_uid
                orm.track_id = session.track.value
                orm.session_type_id = session.session_type.value
                orm.created_at = session.created_at
                orm.steering_assist = session.steering_assist
                orm.braking_assist = session.braking_assist
                orm.gearbox_assist = session.gearbox_assist
                orm.ers_assist = session.ers_assist
                orm.drs_assist = session.drs_assist
                orm.dynamic_racing_line = session.dynamic_racing_line
                orm.corner_cutting_stringency = session.corner_cutting_stringency
            else:
                orm = session_to_orm(session)
                db.add(orm)
                db.flush()          # populate orm.id before commit
                session.id = orm.id

        logger.debug("Session saved: uid=%s id=%d", session.session_uid, session.id)

    def get_by_id(self, session_id: int) -> Session | None:
        with get_session() as db:
            orm = (
                db.query(SessionORM)
                .options(joinedload(SessionORM.laps))
                .filter(SessionORM.id == session_id)
                .first()
            )
            return session_to_domain(orm) if orm else None

    def get_by_uid(self, session_uid: str) -> Session | None:
        with get_session() as db:
            orm = (
                db.query(SessionORM)
                .options(joinedload(SessionORM.laps))
                .filter(SessionORM.session_uid == session_uid)
                .first()
            )
            return session_to_domain(orm) if orm else None

    def get_all(self) -> list[Session]:
        with get_session() as db:
            rows = (
                db.query(SessionORM)
                .options(joinedload(SessionORM.laps))
                .order_by(SessionORM.created_at.desc())
                .all()
            )
            return [session_to_domain(row) for row in rows]

    def delete(self, session_id: int) -> None:
        """Delete a session and cascade to laps and feedbacks.

        Parquet file deletion is handled by the caller (application layer)
        because the repository should not know about the filesystem layout.
        """
        with get_session() as db:
            orm = db.get(SessionORM, session_id)
            if orm is None:
                raise ValueError(f"Session id={session_id} not found.")
            db.delete(orm)

        logger.info("Session deleted: id=%d", session_id)
