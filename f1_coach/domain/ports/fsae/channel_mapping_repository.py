"""ChannelMappingRepository port.

Mappings are session-scoped and are NOT reused across sessions (project
decision — each imported session is labeled independently). This
repository exists so labeling survives an app restart and can be
corrected without re-importing the original CAN log — corrections are
re-decoded from the stored RawCanFrame data + the fixed mapping.
"""

from typing import Protocol

from f1_coach.domain.models.fsae.channel_mapping import ChannelMapping


class ChannelMappingRepository(Protocol):
    """Persistence contract for ChannelMapping rows."""

    def save(self, mapping: ChannelMapping) -> None:
        """Insert or update a channel mapping.

        After a successful call, ``mapping.id`` must reflect the persisted value.
        """
        ...

    def get_by_session(self, session_id: int) -> list[ChannelMapping]:
        """Return all mappings defined for a session, in creation order.

        Used both to populate the Etiketleme screen on reopen and to
        re-decode telemetry after a correction.
        """
        ...

    def delete(self, mapping_id: int) -> None:
        """Remove a single mapping (e.g. user labeled a CAN ID by mistake).

        Raises ValueError if the mapping does not exist.
        """
        ...