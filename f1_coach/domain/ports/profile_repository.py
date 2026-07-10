"""ProfileRepository port.

KOACH has exactly one Profile row (single-user local app), so this
Protocol has no id-based lookup — just "get the current one" and "save it".
"""

from typing import Protocol

from f1_coach.domain.models.profile import Profile


class ProfileRepository(Protocol):
    """Persistence contract for the single-row Profile."""

    def get_current(self) -> Profile | None:
        """Return the profile, or None if onboarding has never completed.

        A None result is the signal the UI uses to route to the Profil
        page on startup instead of Ana Sayfa.
        """
        ...

    def save(self, profile: Profile) -> None:
        """Insert or update the profile.

        After a successful call, ``profile.id`` must reflect the persisted value.
        """
        ...
