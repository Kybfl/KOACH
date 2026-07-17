"""CoachingEngine — orchestrates the full post-lap / post-session feedback flow.

Flow for post-lap feedback:
    1. Analyze the target lap's telemetry (TelemetryAnalyzer)
    2. Determine which reference lap to use (session-best → track-best → none)
    3. Build the prompt (PromptBuilder)
    4. Call the configured AIAdapter
    5. Persist the resulting AIFeedback via LapRepository

This is the only class that touches all of: analysis, prompting, AI adapters,
and repositories — everything else stays single-purpose.
"""

from datetime import datetime

from f1_coach.application.f125.prompt_builder import (
    build_comparison_prompt,
    build_conditions_note,
    build_post_lap_prompt,
    build_setup_comparison_prompt,
    build_setup_single_prompt,
    determine_reference,
)

from f1_coach.application.f125.telemetry_analyzer import analyze_lap

from f1_coach.domain.models.f125.ai_feedback import AIFeedback, FeedbackType
from f1_coach.domain.models.f125.lap import Lap
from f1_coach.domain.models.f125.car_setup import CarSetup
from f1_coach.domain.models.f125.enums import TrackName
from f1_coach.domain.models.f125.setup_feedback import SetupFeedback      

from f1_coach.domain.ports.f125.car_setup_repository import CarSetupRepository
from f1_coach.domain.ports.ai_adapter import AIAdapter
from f1_coach.domain.ports.f125.lap_repository import LapRepository
from f1_coach.domain.ports.f125.session_repository import SessionRepository

from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class CoachingEngine:
    """Generates and persists AI coaching feedback for laps."""

    def __init__(
        self,
        lap_repo: LapRepository,
        session_repo: SessionRepository,
        ai_adapter: AIAdapter,
        car_setup_repo: CarSetupRepository,
    ) -> None:
        self._lap_repo = lap_repo
        self._session_repo = session_repo
        self._ai_adapter = ai_adapter
        self._car_setup_repo = car_setup_repo

    def generate_post_lap_feedback(
        self,
        lap: Lap,
        session_id: int,
        track_id: int,
    ) -> AIFeedback:
        """Generate, persist, and return post-lap feedback for a single lap.

        Applies the reference lap hierarchy:
            1. Session-best lap, if 2+ valid laps exist in this session
            2. All-time best lap for this track, if any prior sessions exist
            3. No reference — general observations only

        Reference candidates are restricted to laps matching the current
        lap's wet/dry condition (see Lap.weather.is_wet) and are never
        safety-car-affected — see LapRepository.get_best_lap[_for_track].

        Args:
            lap:        The lap to analyze (must have telemetry_file set).
            session_id: The current session's database id.
            track_id:   The current track's UDP integer id (TrackName.value).

        Returns:
            The persisted AIFeedback object (with .id populated).

        Raises:
            ValueError: If the lap has no telemetry recorded.
            RuntimeError: If the AI provider call fails.
        """
        current_summary = analyze_lap(lap)
        is_wet = lap.weather.is_wet

        session_laps = self._lap_repo.get_by_session(session_id)
        valid_prior_laps = [
            item for item in session_laps
            if item.is_valid_reference and item.lap_number != lap.lap_number
        ]

        session_best_lap = self._lap_repo.get_best_lap(session_id, is_wet=is_wet)
        session_best_summary = (
            analyze_lap(session_best_lap)
            if session_best_lap and session_best_lap.lap_number != lap.lap_number
            else None
        )

        track_best_lap = self._lap_repo.get_best_lap_for_track(track_id, is_wet=is_wet)
        track_best_summary = (
            analyze_lap(track_best_lap)
            if track_best_lap and track_best_lap.lap_number != lap.lap_number
            else None
        )

        reference = determine_reference(
            session_best=session_best_summary,
            track_best=track_best_summary,
            session_valid_lap_count=len(valid_prior_laps),
        )

        # Reference lap for the conditions/assist note matches whichever
        # level determine_reference() actually picked.
        reference_lap = (
            session_best_lap if reference.level.value == "session_best"
            else track_best_lap if reference.level.value == "track_best"
            else None
        )
        reference_session = (
            self._session_repo.get_by_id(reference_lap.session_id)
            if reference_lap is not None
            else None
        )
        current_session = self._session_repo.get_by_id(session_id)
        conditions_note = (
            build_conditions_note(lap, reference_lap, current_session, reference_session)
            if current_session is not None
            else None
        )

        logger.info(
            "Generating post-lap feedback: lap=%d reference_level=%s",
            lap.lap_number,
            reference.level.value,
        )

        prompt = build_post_lap_prompt(current_summary, reference, conditions_note)
        feedback_text = self._ai_adapter.generate_feedback(prompt)

        feedback = AIFeedback(
            lap_id=lap.id,
            feedback_text=feedback_text,
            feedback_type=FeedbackType.POST_LAP,
            created_at=datetime.now(),
        )
        self._lap_repo.save_feedback(feedback)
        return feedback

    def generate_comparison_feedback(self, lap_a: Lap, lap_b: Lap) -> str:
        """Generate comparative feedback between two explicitly chosen laps.

        Used by the "Karşılaştırmalı Lap Analizi" UI tab. Unlike post-lap
        feedback, this is not persisted to the database — it is generated
        on demand each time the user requests it.

        Args:
            lap_a: First lap to compare.
            lap_b: Second lap to compare.

        Returns:
            The raw feedback text from the AI provider.

        Raises:
            ValueError: If either lap has no telemetry recorded.
            RuntimeError: If the AI provider call fails.
        """
        summary_a = analyze_lap(lap_a)
        summary_b = analyze_lap(lap_b)

        logger.info(
            "Generating comparison feedback: lap_a=%d lap_b=%d",
            lap_a.lap_number,
            lap_b.lap_number,
        )

        prompt = build_comparison_prompt(summary_a, summary_b)
        return self._ai_adapter.generate_feedback(prompt)


    def generate_setup_feedback(self, setup: CarSetup, track: TrackName) -> SetupFeedback:
        """Generate, persist, and return AI analysis for a single car setup.

        Unlike lap coaching, there is no session telemetry link — the
        analysis is limited to general engineering trade-offs implied by
        the setup values themselves (see PromptBuilder's setup preamble).
        """
        logger.info("Generating setup feedback: setup_id=%d", setup.id)

        prompt = build_setup_single_prompt(setup, track)
        feedback_text = self._ai_adapter.generate_feedback(prompt)

        feedback = SetupFeedback(
            setup_id=setup.id,
            feedback_text=feedback_text,
        )
        self._car_setup_repo.save_feedback(feedback)
        return feedback

    def generate_setup_comparison_feedback(
        self, setup_a: CarSetup, setup_b: CarSetup, track: TrackName
    ) -> str:
        """Generate comparative feedback between two setups.

        Not persisted — mirrors generate_comparison_feedback's on-demand,
        ephemeral behaviour for lap comparisons.
        """
        logger.info(
            "Generating setup comparison feedback: setup_a=%d setup_b=%d",
            setup_a.id, setup_b.id,
        )
        prompt = build_setup_comparison_prompt(setup_a, setup_b, track)
        return self._ai_adapter.generate_feedback(prompt)
