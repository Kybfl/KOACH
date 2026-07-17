"""Bidirectional mappers between FSAE ORM rows and domain models.

Same convention as f125_domain_mapper.py: to_domain(orm) -> domain model,
to_orm(domain) -> ORM model (for insert/update). The domain layer has zero
knowledge of SQLAlchemy — these functions carry all the translation logic.
"""

from f1_coach.domain.models.fsae.channel_mapping import ChannelMapping
from f1_coach.domain.models.fsae.vehicle_session import VehicleSession
from f1_coach.infrastructure.storage.orm.fsae_tables import ChannelMappingORM, VehicleSessionORM


# ---------------------------------------------------------------------------
# VehicleSession
# ---------------------------------------------------------------------------


def vehicle_session_to_domain(orm: VehicleSessionORM) -> VehicleSession:
    """Convert a VehicleSessionORM row to a VehicleSession."""
    return VehicleSession(
        name=orm.name,
        source_filename=orm.source_filename,
        raw_can_file=orm.raw_can_file,
        decoded_telemetry_file=orm.decoded_telemetry_file,
        imported_at=orm.imported_at,
        id=orm.id,
    )


def vehicle_session_to_orm(domain: VehicleSession) -> VehicleSessionORM:
    """Convert a VehicleSession domain model to a VehicleSessionORM row."""
    kwargs: dict = dict(
        name=domain.name,
        source_filename=domain.source_filename,
        raw_can_file=domain.raw_can_file,
        decoded_telemetry_file=domain.decoded_telemetry_file,
        imported_at=domain.imported_at,
    )
    if domain.is_persisted:
        kwargs["id"] = domain.id
    return VehicleSessionORM(**kwargs)


# ---------------------------------------------------------------------------
# ChannelMapping
# ---------------------------------------------------------------------------


def channel_mapping_to_domain(orm: ChannelMappingORM) -> ChannelMapping:
    """Convert a ChannelMappingORM row to a ChannelMapping."""
    return ChannelMapping(
        session_id=orm.session_id,
        can_id=orm.can_id,
        start_byte=orm.start_byte,
        bit_length=orm.bit_length,
        little_endian=orm.little_endian,
        signed=orm.signed,
        scale=orm.scale,
        offset=orm.offset,
        name=orm.name,
        unit=orm.unit,
        id=orm.id,
    )


def channel_mapping_to_orm(domain: ChannelMapping) -> ChannelMappingORM:
    """Convert a ChannelMapping domain model to a ChannelMappingORM row."""
    kwargs: dict = dict(
        session_id=domain.session_id,
        can_id=domain.can_id,
        start_byte=domain.start_byte,
        bit_length=domain.bit_length,
        little_endian=domain.little_endian,
        signed=domain.signed,
        scale=domain.scale,
        offset=domain.offset,
        name=domain.name,
        unit=domain.unit,
    )
    if domain.is_persisted:
        kwargs["id"] = domain.id
    return ChannelMappingORM(**kwargs)