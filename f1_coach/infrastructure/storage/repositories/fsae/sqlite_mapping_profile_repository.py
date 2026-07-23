"""SQLite implementation of MappingProfileRepository."""

from sqlalchemy.orm import joinedload

from f1_coach.domain.models.fsae.mapping_profile import MappingProfile, MappingProfileEntry
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.mappers.fsae_domain_mapper import (
    mapping_profile_entry_to_domain,
    mapping_profile_entry_to_orm,
    mapping_profile_to_domain,
    mapping_profile_to_orm,
)
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.fsae_tables import MappingProfileEntryORM, MappingProfileORM

logger = get_logger(__name__)


class SQLiteMappingProfileRepository:
    """Persists and retrieves MappingProfile + entries using SQLite."""

    def save_profile(self, profile: MappingProfile) -> None:
        with get_session() as db:
            if profile.is_persisted:
                orm = db.get(MappingProfileORM, profile.id)
                if orm is None:
                    raise ValueError(f"MappingProfile id={profile.id} not found.")
                orm.name = profile.name
            else:
                orm = mapping_profile_to_orm(profile)
                db.add(orm)
                db.flush()
                profile.id = orm.id

        logger.debug("MappingProfile saved: name=%s id=%d", profile.name, profile.id)

    def get_all_profiles(self) -> list[MappingProfile]:
        with get_session() as db:
            rows = db.query(MappingProfileORM).order_by(MappingProfileORM.name.asc()).all()
            return [mapping_profile_to_domain(row) for row in rows]

    def delete_profile(self, profile_id: int) -> None:
        with get_session() as db:
            orm = db.get(MappingProfileORM, profile_id)
            if orm is None:
                raise ValueError(f"MappingProfile id={profile_id} not found.")
            db.delete(orm)
        logger.info("MappingProfile deleted: id=%d", profile_id)

    def replace_entries(self, profile_id: int, entries: list[MappingProfileEntry]) -> None:
        with get_session() as db:
            db.query(MappingProfileEntryORM).filter(
                MappingProfileEntryORM.profile_id == profile_id
            ).delete()
            for entry in entries:
                entry.id = -1  # replace her zaman yeni satır olarak ekler
                orm = mapping_profile_entry_to_orm(entry)
                orm.profile_id = profile_id
                db.add(orm)

        logger.debug("MappingProfile entries replaced: profile_id=%d count=%d", profile_id, len(entries))

    def get_entries(self, profile_id: int) -> list[MappingProfileEntry]:
        with get_session() as db:
            rows = (
                db.query(MappingProfileEntryORM)
                .filter(MappingProfileEntryORM.profile_id == profile_id)
                .order_by(MappingProfileEntryORM.id.asc())
                .all()
            )
            return [mapping_profile_entry_to_domain(row) for row in rows]