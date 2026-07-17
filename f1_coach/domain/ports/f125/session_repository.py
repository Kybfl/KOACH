"""SessionRepository port — the boundary between application and storage.

The application layer depends only on this Protocol; the SQLite implementation
lives in infrastructure and is injected at runtime. mypy validates structural
compatibility without requiring any inheritance.
"""

from typing import Protocol

from f1_coach.domain.models.f125.session import Session


class SessionRepository(Protocol):
    """Persistence contract for Session aggregates."""

    def save(self, session: Session) -> None:
        """Insert or update a session and return the assigned database id.

        After a successful call, ``session.id`` must reflect the persisted value.
        """
        ...

    def get_by_id(self, session_id: int) -> Session | None:
        """Retrieve a session by its primary key, or None if not found."""
        ...

    def get_by_uid(self, session_uid: str) -> Session | None:
        """Retrieve a session by its UDP UID string, or None if not found."""
        ...

    def get_all(self) -> list[Session]:
        """Return all sessions ordered by created_at descending."""
        ...

    def delete(self, session_id: int) -> None:
        """Delete a session and all its child laps and feedback records.

        Also removes the associated Parquet files from disk.
        Raises ValueError if the session does not exist.
        """
        ...
