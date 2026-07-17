"""Domain port interfaces (Protocols).

These define the boundaries between the application core and external systems.
Import from here to keep call sites stable.
"""

from f1_coach.domain.ports.ai_adapter import AIAdapter
from f1_coach.domain.ports.f125.lap_repository import LapRepository
from f1_coach.domain.ports.profile_repository import ProfileRepository
from f1_coach.domain.ports.f125.session_repository import SessionRepository

__all__ = ["AIAdapter", "LapRepository", "ProfileRepository", "SessionRepository"]
