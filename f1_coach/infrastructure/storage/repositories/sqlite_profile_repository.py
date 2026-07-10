"""SQLite implementation of ProfileRepository.

Single-row semantics: get_current() always returns the first (and only)
row if one exists. save() updates that row if present, otherwise inserts
the first one.
"""

from f1_coach.domain.models.profile import Profile
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.mappers.domain_mapper import (
    profile_to_domain,
    profile_to_orm,
)
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.tables import ProfileORM

logger = get_logger(__name__)


class SQLiteProfileRepository:
    """Persists and retrieves the single Profile row."""

    def get_current(self) -> Profile | None:
        """Return the profile, or None if onboarding has never completed."""
        with get_session() as db:
            orm = db.query(ProfileORM).first()
            return profile_to_domain(orm) if orm else None

    def save(self, profile: Profile) -> None:
        """Insert or update the profile.

        Sets ``profile.id`` after a successful insert.
        """
        with get_session() as db:
            if profile.is_persisted:
                orm = db.get(ProfileORM, profile.id)
                if orm is None:
                    raise ValueError(f"Profile id={profile.id} not found in database.")
                orm.name = profile.name
                orm.email = profile.email
                orm.favorite_team = profile.favorite_team
                orm.favorite_driver = profile.favorite_driver
                orm.favorite_track = profile.favorite_track
                orm.photo_path = profile.photo_path
                orm.photo_path = profile.photo_path
                orm.ai_provider = profile.ai_provider
                orm.udp_port = profile.udp_port
                orm.theme = profile.theme
                orm.ui_scale = profile.ui_scale
            else:
                orm = profile_to_orm(profile)
                db.add(orm)
                db.flush()
                profile.id = orm.id

        logger.info("Profile saved: name=%s id=%d", profile.name, profile.id)
