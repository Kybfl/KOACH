"""Application layer — orchestrates domain and infrastructure.

Import from here to keep call sites stable.
"""

from f1_coach.application.f125.coaching_engine import CoachingEngine
from f1_coach.application.f125.prompt_builder import (
    ReferenceContext,
    ReferenceLevel,
    build_comparison_prompt,
    build_conditions_note,
    build_post_lap_prompt,
    determine_reference,
)
from f1_coach.application.f125.telemetry_analyzer import LapSummary, SectorSummary, analyze_lap

__all__ = [
    "CoachingEngine",
    "ReferenceContext",
    "ReferenceLevel",
    "build_comparison_prompt",
    "build_conditions_note",
    "build_post_lap_prompt",
    "determine_reference",
    "LapSummary",
    "SectorSummary",
    "analyze_lap",
]
