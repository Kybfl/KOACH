"""SQLite implementation of CarSetupRepository.

Each row represents one detected setup change within a session (see
SessionManager.on_car_setup_packet for the dedup logic that keeps a
continuous UDP broadcast from producing a row per frame). Rows are
append-only — there is no update path here.
"""

from f1_coach.domain.models.f125.car_setup import CarSetup
from f1_coach.domain.models.f125.setup_feedback import SetupFeedback

from f1_coach.infrastructure.logging.logger import get_logger

from f1_coach.infrastructure.storage.mappers.f125_domain_mapper import (
    car_setup_to_domain,
    car_setup_to_orm,
    setup_feedback_to_domain,   
    setup_feedback_to_orm,
)
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.f125_tables import CarSetupFeedbackORM, CarSetupORM

logger = get_logger(__name__)


class SQLiteCarSetupRepository:
    """Persists and retrieves CarSetup rows for a session."""

    def save(self, setup: CarSetup) -> None:
        """Insert a new setup record. Sets ``setup.id`` after a successful insert."""
        with get_session() as db:
            orm = car_setup_to_orm(setup)
            db.add(orm)
            db.flush()
            setup.id = orm.id

        logger.info(
            "Car setup saved: session_id=%d valid_from_lap=%d id=%d",
            setup.session_id, setup.valid_from_lap, setup.id,
        )

    def get_by_session(self, session_id: int) -> list[CarSetup]:
        with get_session() as db:
            rows = (
                db.query(CarSetupORM)
                .filter(CarSetupORM.session_id == session_id)
                .order_by(CarSetupORM.valid_from_lap.asc())
                .all()
            )
            return [car_setup_to_domain(row) for row in rows]
        
    def save_feedback(self, feedback: SetupFeedback) -> None:
        """Persist AI feedback for a setup. Sets ``feedback.id`` after insert."""
        with get_session() as db:
            if feedback.is_persisted:
                orm = db.get(CarSetupFeedbackORM, feedback.id)
                if orm is None:
                    raise ValueError(f"SetupFeedback id={feedback.id} not found.")
                orm.feedback_text = feedback.feedback_text
            else:
                orm = setup_feedback_to_orm(feedback)
                db.add(orm)
                db.flush()
                feedback.id = orm.id

        logger.debug("Setup feedback saved: setup_id=%d id=%d", feedback.setup_id, feedback.id)

    def get_feedback(self, setup_id: int) -> SetupFeedback | None:
        with get_session() as db:
            orm = (
                db.query(CarSetupFeedbackORM)
                .filter(CarSetupFeedbackORM.setup_id == setup_id)
                .order_by(CarSetupFeedbackORM.created_at.desc())
                .first()
            )
            return setup_feedback_to_domain(orm) if orm else None