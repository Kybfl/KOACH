"""SQLAlchemy ORM table definitions.

These classes represent the database schema and are completely separate from
the domain models. The mapper layer (mappers/session_mapper.py etc.) handles
conversion between the two worlds.

Schema overview:
    sessions      — one row per game session
    laps          — one row per completed lap, FK → sessions
    ai_feedbacks  — one row per feedback generation, FK → laps
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SessionORM(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    session_type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    steering_assist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    braking_assist: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gearbox_assist: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    ers_assist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    drs_assist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dynamic_racing_line: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    corner_cutting_stringency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    laps: Mapped[list["LapORM"]] = relationship(
        "LapORM",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="LapORM.lap_number",
    )


class LapORM(Base):
    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap_time: Mapped[float] = mapped_column(Float, nullable=False)
    sector_1_time: Mapped[float] = mapped_column(Float, nullable=False)
    sector_2_time: Mapped[float] = mapped_column(Float, nullable=False)
    sector_3_time: Mapped[float] = mapped_column(Float, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tyre_compound: Mapped[int] = mapped_column(Integer, nullable=False)
    weather_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safety_car_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    track_temperature: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    air_temperature: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    telemetry_file: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    status_file: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    position_file: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    session: Mapped["SessionORM"] = relationship("SessionORM", back_populates="laps")
    feedbacks: Mapped[list["AIFeedbackORM"]] = relationship(
        "AIFeedbackORM",
        back_populates="lap",
        cascade="all, delete-orphan",
        order_by="AIFeedbackORM.created_at.desc()",
    )


class AIFeedbackORM(Base):
    __tablename__ = "ai_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lap_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("laps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    lap: Mapped["LapORM"] = relationship("LapORM", back_populates="feedbacks")


class ProfileORM(Base):
    """Single-row table — KOACH is a local single-user application.

    Faz 6 will extend this with AI provider settings (ai_provider,
    ai_api_key, udp_port, theme, etc.) once the Ayarlar screen is designed.
    """

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    favorite_team: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    favorite_driver: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    favorite_track: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    photo_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    photo_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    ai_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    udp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=20777)
    theme: Mapped[str] = mapped_column(String(16), nullable=False, default="dark")
    ui_scale: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class CarSetupORM(Base):
    """One row per detected setup change within a session (append-only)."""

    __tablename__ = "car_setups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valid_from_lap: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    front_wing: Mapped[int] = mapped_column(Integer, nullable=False)
    rear_wing: Mapped[int] = mapped_column(Integer, nullable=False)
    on_throttle_diff: Mapped[int] = mapped_column(Integer, nullable=False)
    off_throttle_diff: Mapped[int] = mapped_column(Integer, nullable=False)
    front_camber: Mapped[float] = mapped_column(Float, nullable=False)
    rear_camber: Mapped[float] = mapped_column(Float, nullable=False)
    front_toe: Mapped[float] = mapped_column(Float, nullable=False)
    rear_toe: Mapped[float] = mapped_column(Float, nullable=False)
    front_suspension: Mapped[int] = mapped_column(Integer, nullable=False)
    rear_suspension: Mapped[int] = mapped_column(Integer, nullable=False)
    front_arb: Mapped[int] = mapped_column(Integer, nullable=False)
    rear_arb: Mapped[int] = mapped_column(Integer, nullable=False)
    front_ride_height: Mapped[int] = mapped_column(Integer, nullable=False)
    rear_ride_height: Mapped[int] = mapped_column(Integer, nullable=False)
    brake_pressure: Mapped[int] = mapped_column(Integer, nullable=False)
    brake_bias: Mapped[int] = mapped_column(Integer, nullable=False)
    front_left_tyre_pressure: Mapped[float] = mapped_column(Float, nullable=False)
    front_right_tyre_pressure: Mapped[float] = mapped_column(Float, nullable=False)
    rear_left_tyre_pressure: Mapped[float] = mapped_column(Float, nullable=False)
    rear_right_tyre_pressure: Mapped[float] = mapped_column(Float, nullable=False)
    ballast: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_load: Mapped[float] = mapped_column(Float, nullable=False)

class CarSetupFeedbackORM(Base):
    """AI analysis text for a single car setup. Comparison feedback is
    never persisted — only single-setup analysis reaches this table."""

    __tablename__ = "car_setup_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setup_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("car_setups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)