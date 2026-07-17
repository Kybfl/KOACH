"""SetupFeedback domain model.

AI-generated analysis for a single CarSetup. Setup *comparison* feedback
is deliberately NOT modeled here — it stays unpersisted, mirroring how lap
comparison feedback already works (see CoachingEngine.generate_comparison_feedback).
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SetupFeedback:
    """AI-generated analysis for a single CarSetup.

    Attributes:
        setup_id:      Foreign key to the CarSetup this feedback belongs to.
        feedback_text: The raw text produced by the AI adapter.
        created_at:    When the feedback was generated.
        id:            Database primary key; -1 means not yet persisted.
    """

    setup_id: int
    feedback_text: str
    created_at: datetime = field(default_factory=datetime.now)
    id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1