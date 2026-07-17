"""LapRepository port.

AIFeedback is managed here (not in a separate repository) because feedback is
always accessed in the context of a specific lap.
"""

from typing import Protocol

from f1_coach.domain.models.f125.ai_feedback import AIFeedback
from f1_coach.domain.models.f125.lap import Lap


class LapRepository(Protocol):
    """Persistence contract for Lap aggregates and their AI feedback."""

    def save(self, lap: Lap) -> None:
        """Insert or update a lap.

        After a successful call, ``lap.id`` must reflect the persisted value.
        """
        ...

    def get_by_session(self, session_id: int) -> list[Lap]:
        """Return all laps for a session, ordered by lap_number ascending."""
        ...

    def get_best_lap(self, session_id: int, is_wet: bool | None = None) -> Lap | None:
        """Return the fastest reference-eligible lap in a session, or None.

        Excludes invalid laps and safety-car-affected laps (see
        Lap.is_valid_reference). If ``is_wet`` is given, only laps whose
        weather condition matches (wet vs dry) are considered — comparing
        a dry lap against a wet reference would be misleading.
        """
        ...

    def get_best_lap_for_track(self, track_id: int, is_wet: bool | None = None) -> Lap | None:
        """Return the all-time fastest reference-eligible lap on a track, or None.

        Used by CoachingEngine when there are fewer than 2 valid laps in the
        current session (second level of the reference lap hierarchy).
        Same exclusion and weather-matching rules as get_best_lap().
        """
        ...

    def save_feedback(self, feedback: AIFeedback) -> None:
        """Persist AI feedback for a lap.

        After a successful call, ``feedback.id`` must reflect the persisted value.
        """
        ...

    def get_feedback(self, lap_id: int) -> AIFeedback | None:
        """Return the most recent feedback for a lap, or None if none exists."""
        ...
