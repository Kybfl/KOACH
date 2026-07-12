"""Bidirectional mappers between ORM rows and domain models.

The domain layer has zero knowledge of SQLAlchemy. These mapper functions
sit in the infrastructure layer and carry all the translation logic.

Convention:
    to_domain(orm_obj)   → domain model
    to_orm(domain_obj)   → ORM model (for insert/update)
"""

from datetime import datetime

from f1_coach.domain.models.ai_feedback import AIFeedback, FeedbackType
from f1_coach.domain.models.enums import SessionType, TrackName, WeatherCondition
from f1_coach.domain.models.lap import Lap
from f1_coach.domain.models.profile import Profile
from f1_coach.domain.models.session import Session
from f1_coach.infrastructure.storage.orm.tables import (
    AIFeedbackORM,
    LapORM,
    ProfileORM,
    SessionORM,
)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


def session_to_domain(orm: SessionORM) -> Session:
    """Convert a SessionORM row (with eagerly loaded laps) to a Session."""
    session = Session(
        session_uid=orm.session_uid,
        track=TrackName.from_udp(orm.track_id),
        session_type=SessionType.from_udp(orm.session_type_id),
        created_at=orm.created_at,
        steering_assist=orm.steering_assist,
        braking_assist=orm.braking_assist,
        gearbox_assist=orm.gearbox_assist,
        ers_assist=orm.ers_assist,
        drs_assist=orm.drs_assist,
        dynamic_racing_line=orm.dynamic_racing_line,
        corner_cutting_stringency=orm.corner_cutting_stringency,
        laps=[lap_to_domain(lap_orm) for lap_orm in orm.laps],
        id=orm.id,
    )
    return session


def session_to_orm(domain: Session) -> SessionORM:
    """Convert a Session domain model to a SessionORM row.

    Does not include laps — laps are persisted separately via LapRepository.
    """
    kwargs: dict = dict(
        session_uid=domain.session_uid,
        track_id=domain.track.value,
        session_type_id=domain.session_type.value,
        created_at=domain.created_at,
        steering_assist=domain.steering_assist,
        braking_assist=domain.braking_assist,
        gearbox_assist=domain.gearbox_assist,
        ers_assist=domain.ers_assist,
        drs_assist=domain.drs_assist,
        dynamic_racing_line=domain.dynamic_racing_line,
        corner_cutting_stringency=domain.corner_cutting_stringency,
    )
    if domain.is_persisted:
        kwargs["id"] = domain.id
    return SessionORM(**kwargs)


# ---------------------------------------------------------------------------
# Lap
# ---------------------------------------------------------------------------


def lap_to_domain(orm: LapORM) -> Lap:
    """Convert a LapORM row to a Lap domain model."""
    return Lap(
        lap_number=orm.lap_number,
        lap_time=orm.lap_time,
        sector_1_time=orm.sector_1_time,
        sector_2_time=orm.sector_2_time,
        sector_3_time=orm.sector_3_time,
        is_valid=orm.is_valid,
        tyre_compound=orm.tyre_compound,
        weather=WeatherCondition.from_udp(orm.weather_id),
        safety_car_active=orm.safety_car_active,
        track_temperature=orm.track_temperature,
        air_temperature=orm.air_temperature,
        telemetry_file=orm.telemetry_file,
        status_file=orm.status_file,
        position_file=orm.position_file,
        id=orm.id,
        session_id=orm.session_id,
    )


def lap_to_orm(domain: Lap) -> LapORM:
    """Convert a Lap domain model to a LapORM row."""
    kwargs: dict = dict(
        session_id=domain.session_id,
        lap_number=domain.lap_number,
        lap_time=domain.lap_time,
        sector_1_time=domain.sector_1_time,
        sector_2_time=domain.sector_2_time,
        sector_3_time=domain.sector_3_time,
        is_valid=domain.is_valid,
        tyre_compound=domain.tyre_compound,
        weather_id=domain.weather.value,
        safety_car_active=domain.safety_car_active,
        track_temperature=domain.track_temperature,
        air_temperature=domain.air_temperature,
        telemetry_file=domain.telemetry_file,
        status_file=domain.status_file,
        position_file=domain.position_file,
    )
    if domain.is_persisted:
        kwargs["id"] = domain.id
    return LapORM(**kwargs)


# ---------------------------------------------------------------------------
# AIFeedback
# ---------------------------------------------------------------------------


def feedback_to_domain(orm: AIFeedbackORM) -> AIFeedback:
    """Convert an AIFeedbackORM row to an AIFeedback domain model."""
    return AIFeedback(
        lap_id=orm.lap_id,
        feedback_text=orm.feedback_text,
        feedback_type=FeedbackType(orm.feedback_type),
        created_at=orm.created_at,
        id=orm.id,
    )


def feedback_to_orm(domain: AIFeedback) -> AIFeedbackORM:
    """Convert an AIFeedback domain model to an AIFeedbackORM row."""
    kwargs: dict = dict(
        lap_id=domain.lap_id,
        feedback_text=domain.feedback_text,
        feedback_type=domain.feedback_type.value,
        created_at=domain.created_at,
    )
    if domain.is_persisted:
        kwargs["id"] = domain.id
    return AIFeedbackORM(**kwargs)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def profile_to_domain(orm: ProfileORM) -> Profile:
    """Convert a ProfileORM row to a Profile domain model."""
    return Profile(
        name=orm.name,
        email=orm.email,
        favorite_team=orm.favorite_team,
        favorite_driver=orm.favorite_driver,
        favorite_track=orm.favorite_track,
        photo_path=orm.photo_path,
        ai_provider=orm.ai_provider,
        udp_port=orm.udp_port,
        theme=orm.theme,
        ui_scale=orm.ui_scale,
        created_at=orm.created_at,
        id=orm.id,
    )


def profile_to_orm(domain: Profile) -> ProfileORM:
    """Convert a Profile domain model to a ProfileORM row."""
    kwargs: dict = dict(
        name=domain.name,
        email=domain.email,
        favorite_team=domain.favorite_team,
        favorite_driver=domain.favorite_driver,
        favorite_track=domain.favorite_track,
        photo_path=domain.photo_path,
        ai_provider=domain.ai_provider,
        udp_port=domain.udp_port,
        theme=domain.theme,
        ui_scale=domain.ui_scale,
        created_at=domain.created_at,
    )
    if domain.is_persisted:
        kwargs["id"] = domain.id
    return ProfileORM(**kwargs)

