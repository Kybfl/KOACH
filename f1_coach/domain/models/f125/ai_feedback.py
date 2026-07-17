"""AIFeedback domain model.

Feedback is always created in the context of a specific lap, which is why it is
managed through LapRepository rather than a dedicated repository.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class FeedbackType(Enum):
    POST_LAP = "post_lap"
    POST_SESSION = "post_session"


@dataclass
class AIFeedback:
    """AI-generated coaching feedback for a lap.

    Attributes:
        lap_id:        Foreign key to the Lap this feedback belongs to.
        feedback_text: The raw text produced by the AI adapter.
        feedback_type: Whether this was generated after a single lap or at
                       session end.
        created_at:    When the feedback was generated.
        id:            Database primary key; -1 means not yet persisted.
    """

    lap_id: int
    feedback_text: str
    feedback_type: FeedbackType
    created_at: datetime = field(default_factory=datetime.now)
    id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1
