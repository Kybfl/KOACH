"""SQLite implementation of VehicleSessionRepository."""

from sqlalchemy.orm import joinedload

from f1_coach.domain.models.fsae.vehicle_session import VehicleSession
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.mappers.fsae_domain_mapper import (
    vehicle_session_to_domain,
    vehicle_session_to_orm,
)
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.fsae_tables import VehicleSessionORM

logger = get_logger(__name__)


class SQLiteVehicleSessionRepository:
    """Persists and retrieves VehicleSession aggregates using SQLite via SQLAlchemy."""

    def save(self, session: VehicleSession) -> None:
        """Insert a new session or update an existing one.

        Sets ``session.id`` after a successful insert.
        """
        with get_session() as db:
            if session.is_persisted:
                orm = db.get(VehicleSessionORM, session.id)
                if orm is None:
                    raise ValueError(f"VehicleSession id={session.id} not found in database.")
                orm.name = session.name
                orm.source_filename = session.source_filename
                orm.raw_can_file = session.raw_can_file
                orm.decoded_telemetry_file = session.decoded_telemetry_file
                orm.imported_at = session.imported_at
            else:
                orm = vehicle_session_to_orm(session)
                db.add(orm)
                db.flush()
                session.id = orm.id

        logger.debug("VehicleSession saved: name=%s id=%d", session.name, session.id)

    def get_by_id(self, session_id: int) -> VehicleSession | None:
        with get_session() as db:
            orm = (
                db.query(VehicleSessionORM)
                .options(joinedload(VehicleSessionORM.mappings))
                .filter(VehicleSessionORM.id == session_id)
                .first()
            )
            return vehicle_session_to_domain(orm) if orm else None

    def get_all(self) -> list[VehicleSession]:
        with get_session() as db:
            rows = (
                db.query(VehicleSessionORM)
                .order_by(VehicleSessionORM.imported_at.desc())
                .all()
            )
            return [vehicle_session_to_domain(row) for row in rows]

    def delete(self, session_id: int) -> None:
        """Delete a session and cascade to its channel mappings.

        Parquet file deletion is handled by the caller (application layer)
        via infrastructure/storage/fsae/parquet_writer.delete_session_files —
        same convention as F1 25's SessionRepository.delete().
        """
        with get_session() as db:
            orm = db.get(VehicleSessionORM, session_id)
            if orm is None:
                raise ValueError(f"VehicleSession id={session_id} not found.")
            db.delete(orm)

        logger.info("VehicleSession deleted: id=%d", session_id)