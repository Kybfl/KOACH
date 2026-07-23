"""SQLAlchemy ORM table definitions for the FSAE module.

Mirrors the F1 25 module's storage pattern: SQLite holds relational
metadata + file paths, actual telemetry lives in Parquet (see
infrastructure/storage/fsae/parquet_writer.py). Shares the same Base
(and therefore the same koach.db file) as the F1 25 tables module —
see base.py.

Schema overview:
    vehicle_sessions  — one row per imported CAN log
    channel_mappings  — one row per labeled signal, FK -> vehicle_sessions
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from f1_coach.infrastructure.storage.orm.base import Base


class VehicleSessionORM(Base):
    __tablename__ = "vehicle_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_can_file: Mapped[str] = mapped_column(String(512), nullable=False)
    decoded_telemetry_file: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    mappings: Mapped[list["ChannelMappingORM"]] = relationship(
        "ChannelMappingORM",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChannelMappingORM.id",
    )


class ChannelMappingORM(Base):
    __tablename__ = "channel_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicle_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    can_id: Mapped[int] = mapped_column(Integer, nullable=False)
    start_byte: Mapped[int] = mapped_column(Integer, nullable=False)
    bit_length: Mapped[int] = mapped_column(Integer, nullable=False)
    little_endian: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scale: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    offset: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    session: Mapped["VehicleSessionORM"] = relationship("VehicleSessionORM", back_populates="mappings")

class MappingProfileORM(Base):
    __tablename__ = "mapping_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    entries: Mapped[list["MappingProfileEntryORM"]] = relationship(
        "MappingProfileEntryORM",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="MappingProfileEntryORM.id",
    )


class MappingProfileEntryORM(Base):
    __tablename__ = "mapping_profile_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mapping_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    can_id: Mapped[int] = mapped_column(Integer, nullable=False)
    start_byte: Mapped[int] = mapped_column(Integer, nullable=False)
    bit_length: Mapped[int] = mapped_column(Integer, nullable=False)
    little_endian: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scale: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    offset: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    profile: Mapped["MappingProfileORM"] = relationship("MappingProfileORM", back_populates="entries")