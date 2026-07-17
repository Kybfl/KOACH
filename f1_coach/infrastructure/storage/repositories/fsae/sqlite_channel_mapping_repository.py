"""SQLite implementation of ChannelMappingRepository."""

from f1_coach.domain.models.fsae.channel_mapping import ChannelMapping
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.mappers.fsae_domain_mapper import (
    channel_mapping_to_domain,
    channel_mapping_to_orm,
)
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.fsae_tables import ChannelMappingORM

logger = get_logger(__name__)


class SQLiteChannelMappingRepository:
    """Persists and retrieves ChannelMapping rows for a VehicleSession."""

    def save(self, mapping: ChannelMapping) -> None:
        """Insert a new mapping or update an existing one.

        Sets ``mapping.id`` after a successful insert.
        """
        with get_session() as db:
            if mapping.is_persisted:
                orm = db.get(ChannelMappingORM, mapping.id)
                if orm is None:
                    raise ValueError(f"ChannelMapping id={mapping.id} not found in database.")
                orm.can_id = mapping.can_id
                orm.start_byte = mapping.start_byte
                orm.bit_length = mapping.bit_length
                orm.little_endian = mapping.little_endian
                orm.signed = mapping.signed
                orm.scale = mapping.scale
                orm.offset = mapping.offset
                orm.name = mapping.name
                orm.unit = mapping.unit
            else:
                orm = channel_mapping_to_orm(mapping)
                db.add(orm)
                db.flush()
                mapping.id = orm.id

        logger.debug(
            "ChannelMapping saved: session_id=%d can_id=0x%X name=%s id=%d",
            mapping.session_id, mapping.can_id, mapping.name, mapping.id,
        )

    def get_by_session(self, session_id: int) -> list[ChannelMapping]:
        with get_session() as db:
            rows = (
                db.query(ChannelMappingORM)
                .filter(ChannelMappingORM.session_id == session_id)
                .order_by(ChannelMappingORM.id.asc())
                .all()
            )
            return [channel_mapping_to_domain(row) for row in rows]

    def delete(self, mapping_id: int) -> None:
        with get_session() as db:
            orm = db.get(ChannelMappingORM, mapping_id)
            if orm is None:
                raise ValueError(f"ChannelMapping id={mapping_id} not found.")
            db.delete(orm)

        logger.debug("ChannelMapping deleted: id=%d", mapping_id)