"""CarSetupRepository port.

Setup rows are append-only within a session — see SessionManager for the
change-detection logic that decides when a new row should be written.
There is no update/delete beyond what SessionRepository.delete() already
cascades.
"""

from typing import Protocol

from f1_coach.domain.models.f125.car_setup import CarSetup
from f1_coach.domain.models.f125.setup_feedback import SetupFeedback   

class CarSetupRepository(Protocol):
    """Persistence contract for CarSetup records and their AI feedback."""

    def save(self, setup: CarSetup) -> None:
        ...

    def get_by_session(self, session_id: int) -> list[CarSetup]:
        ...

    def save_feedback(self, feedback: SetupFeedback) -> None:
        """Persist AI feedback for a single setup.

        After a successful call, ``feedback.id`` must reflect the persisted value.
        """
        ...

    def get_feedback(self, setup_id: int) -> SetupFeedback | None:
        """Return the most recent feedback for a setup, or None if none exists."""
        ...