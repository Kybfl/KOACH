"""VehicleSessionRepository port — the boundary between the application and storage.

Parallel to F1 25's SessionRepository, but without a lap concept — see
VehicleSession's docstring for why FSAE sessions stay flat rather than
being broken into laps.
"""

from typing import Protocol

from f1_coach.domain.models.fsae.vehicle_session import VehicleSession


class VehicleSessionRepository(Protocol):
    """Persistence contract for VehicleSession aggregates."""

    def save(self, session: VehicleSession) -> None:
        """Insert or update a session.

        After a successful call, ``session.id`` must reflect the persisted value.
        """
        ...

    def get_by_id(self, session_id: int) -> VehicleSession | None:
        """Retrieve a session by its primary key, or None if not found."""
        ...

    def get_all(self) -> list[VehicleSession]:
        """Return all sessions ordered by imported_at descending."""
        ...

    def delete(self, session_id: int) -> None:
        """Delete a session and cascade to its channel mappings.

        Also removes the associated raw/decoded Parquet files from disk —
        the caller (application layer) handles filesystem deletion, same
        convention as SessionRepository.delete() in the F1 25 module.
        """
        ...