"""SQLite implementation of LapRepository.

Also manages AIFeedback persistence, since feedback is always accessed
in the context of a specific lap.
"""

from f1_coach.domain.models.ai_feedback import AIFeedback
from f1_coach.domain.models.enums import WeatherCondition
from f1_coach.domain.models.lap import Lap
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.mappers.domain_mapper import (
    feedback_to_domain,
    feedback_to_orm,
    lap_to_domain,
    lap_to_orm,
)
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.tables import AIFeedbackORM, LapORM, SessionORM

logger = get_logger(__name__)

# Weather ids where WeatherCondition.is_wet is False (see enums.py)
_DRY_WEATHER_IDS = (
    WeatherCondition.CLEAR.value,
    WeatherCondition.LIGHT_CLOUD.value,
    WeatherCondition.OVERCAST.value,
)
_WET_WEATHER_IDS = (
    WeatherCondition.LIGHT_RAIN.value,
    WeatherCondition.HEAVY_RAIN.value,
    WeatherCondition.STORM.value,
)


class SQLiteLapRepository:
    """Persists and retrieves Lap aggregates and their AI feedback."""

    def save(self, lap: Lap) -> None:
        """Insert a new lap or update an existing one.

        Sets ``lap.id`` after a successful insert.
        """
        with get_session() as db:
            if lap.is_persisted:
                orm = db.get(LapORM, lap.id)
                if orm is None:
                    raise ValueError(f"Lap id={lap.id} not found in database.")
                orm.lap_time = lap.lap_time
                orm.sector_1_time = lap.sector_1_time
                orm.sector_2_time = lap.sector_2_time
                orm.sector_3_time = lap.sector_3_time
                orm.is_valid = lap.is_valid
                orm.tyre_compound = lap.tyre_compound
                orm.weather_id = lap.weather.value
                orm.safety_car_active = lap.safety_car_active
                orm.track_temperature = lap.track_temperature
                orm.air_temperature = lap.air_temperature
                orm.telemetry_file = lap.telemetry_file
                orm.status_file = lap.status_file
            else:
                orm = lap_to_orm(lap)
                db.add(orm)
                db.flush()
                lap.id = orm.id

        logger.debug(
            "Lap saved: session_id=%d lap_number=%d id=%d",
            lap.session_id,
            lap.lap_number,
            lap.id,
        )

    def get_by_session(self, session_id: int) -> list[Lap]:
        with get_session() as db:
            rows = (
                db.query(LapORM)
                .filter(LapORM.session_id == session_id)
                .order_by(LapORM.lap_number.asc())
                .all()
            )
            return [lap_to_domain(row) for row in rows]

    def get_best_lap(self, session_id: int, is_wet: bool | None = None) -> Lap | None:
        """Return the fastest reference-eligible lap in a session."""
        with get_session() as db:
            query = db.query(LapORM).filter(
                LapORM.session_id == session_id,
                LapORM.is_valid.is_(True),
                LapORM.safety_car_active.is_(False),
            )
            query = self._apply_weather_filter(query, is_wet)
            orm = query.order_by(LapORM.lap_time.asc()).first()
            return lap_to_domain(orm) if orm else None

    def get_best_lap_for_track(self, track_id: int, is_wet: bool | None = None) -> Lap | None:
        """Return the all-time fastest reference-eligible lap on a given track.

        Joins through sessions to filter by track_id.
        Used by CoachingEngine as the second level of the reference lap hierarchy.
        """
        with get_session() as db:
            query = (
                db.query(LapORM)
                .join(SessionORM, LapORM.session_id == SessionORM.id)
                .filter(
                    SessionORM.track_id == track_id,
                    LapORM.is_valid.is_(True),
                    LapORM.safety_car_active.is_(False),
                )
            )
            query = self._apply_weather_filter(query, is_wet)
            orm = query.order_by(LapORM.lap_time.asc()).first()
            return lap_to_domain(orm) if orm else None

    @staticmethod
    def _apply_weather_filter(query, is_wet: bool | None):
        """Restrict a lap query to matching wet/dry weather ids.

        A None value applies no filter — used when the caller doesn't need
        weather-matched references (e.g. general listing queries).
        """
        if is_wet is None:
            return query
        allowed_ids = _WET_WEATHER_IDS if is_wet else _DRY_WEATHER_IDS
        return query.filter(LapORM.weather_id.in_(allowed_ids))

    def save_feedback(self, feedback: AIFeedback) -> None:
        """Persist AI feedback. Sets ``feedback.id`` after a successful insert."""
        with get_session() as db:
            if feedback.is_persisted:
                orm = db.get(AIFeedbackORM, feedback.id)
                if orm is None:
                    raise ValueError(f"AIFeedback id={feedback.id} not found.")
                orm.feedback_text = feedback.feedback_text
            else:
                orm = feedback_to_orm(feedback)
                db.add(orm)
                db.flush()
                feedback.id = orm.id

        logger.debug("Feedback saved: lap_id=%d id=%d", feedback.lap_id, feedback.id)

    def get_feedback(self, lap_id: int) -> AIFeedback | None:
        """Return the most recently generated feedback for a lap, or None."""
        with get_session() as db:
            orm = (
                db.query(AIFeedbackORM)
                .filter(AIFeedbackORM.lap_id == lap_id)
                .order_by(AIFeedbackORM.created_at.desc())
                .first()
            )
            return feedback_to_domain(orm) if orm else None
