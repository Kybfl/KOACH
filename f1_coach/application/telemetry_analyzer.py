"""TelemetryAnalyzer — sector-level telemetry summarisation.

Lives in the application layer (not domain) because it depends on the
Parquet storage infrastructure to load raw telemetry — the domain layer
must stay free of infrastructure concerns per the hexagonal architecture.

Per project principle: AI feedback scope is sector-based only. This analyzer
deliberately does NOT attempt to pinpoint exact braking points, apex metres,
or other unverifiable micro-claims (e.g. "you braked 3 meters early"). Instead
it produces aggregate, defensible sector statistics that a prompt can safely
reference.

Track position boundaries for sectors are approximated using the average
position at which m_sector transitions from 0→1 and 1→2 within the lap's
own telemetry — since TelemetryPoint does not carry a raw sector field,
sector boundaries are derived from the Lap's own sector time proportions
mapped onto track_position at the analysis layer instead of guessed from
absolute distance.
"""

from dataclasses import dataclass

import pandas as pd

from f1_coach.domain.models.lap import Lap
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.parquet_writer import read_car_status, read_telemetry

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SectorSummary:
    """Aggregate statistics for one sector of a lap.

    All values are averages or maxima over the sector's telemetry frames —
    never single-frame claims — to stay within the "sector-based only,
    no unverifiable micro-claims" feedback scope.
    """

    sector_number: int          # 1, 2, or 3
    sector_time: float
    avg_speed: float
    max_speed: float
    avg_throttle: float
    avg_brake: float
    full_throttle_pct: float    # % of frames with throttle >= 0.98
    braking_frames_pct: float   # % of frames with brake > 0.05
    drs_usage_pct: float        # % of frames with DRS active


@dataclass(frozen=True, slots=True)
class LapSummary:
    """Full sector-by-sector summary for one lap, ready for prompt building."""

    lap_number: int
    lap_time: float
    is_valid: bool
    sectors: tuple[SectorSummary, SectorSummary, SectorSummary]


def _sector_bounds(lap: Lap) -> tuple[float, float]:
    """Compute approximate track_position boundaries between sectors.

    Uses the proportion of sector time relative to total lap time as a proxy
    for the proportion of the lap distance — an approximation, not a claim
    about exact geometry, which is acceptable for sector-level aggregation.

    Returns:
        (sector1_end_position, sector2_end_position) in the 0.0–1.0 range.
    """
    total = lap.lap_time
    if total <= 0:
        return 1 / 3, 2 / 3
    s1_end = lap.sector_1_time / total
    s2_end = s1_end + (lap.sector_2_time / total)
    return min(s1_end, 0.99), min(s2_end, 0.999)


def analyze_lap(lap: Lap) -> LapSummary:
    """Load a lap's Parquet telemetry and produce a sector-by-sector summary.

    Args:
        lap: A persisted Lap with valid telemetry_file / status_file paths.

    Returns:
        LapSummary with three SectorSummary entries.

    Raises:
        ValueError: If the lap has no telemetry file recorded.
    """
    if not lap.telemetry_file:
        raise ValueError(f"Lap {lap.lap_number} has no telemetry file to analyze.")

    telemetry = read_telemetry(lap.telemetry_file)
    status = read_car_status(lap.status_file) if lap.status_file else None

    s1_end, s2_end = _sector_bounds(lap)

    bounds = [
        (0.0, s1_end, lap.sector_1_time, 1),
        (s1_end, s2_end, lap.sector_2_time, 2),
        (s2_end, 1.0, lap.sector_3_time, 3),
    ]

    sectors: list[SectorSummary] = []
    for start, end, sector_time, sector_num in bounds:
        mask = (telemetry["track_position"] >= start) & (telemetry["track_position"] < end)
        segment = telemetry[mask]

        if segment.empty:
            logger.warning(
                "Empty telemetry segment for lap %d sector %d — skipping stats.",
                lap.lap_number,
                sector_num,
            )
            sectors.append(
                SectorSummary(
                    sector_number=sector_num,
                    sector_time=sector_time,
                    avg_speed=0.0,
                    max_speed=0.0,
                    avg_throttle=0.0,
                    avg_brake=0.0,
                    full_throttle_pct=0.0,
                    braking_frames_pct=0.0,
                    drs_usage_pct=0.0,
                )
            )
            continue

        sectors.append(
            SectorSummary(
                sector_number=sector_num,
                sector_time=sector_time,
                avg_speed=float(segment["speed"].mean()),
                max_speed=float(segment["speed"].max()),
                avg_throttle=float(segment["throttle"].mean()),
                avg_brake=float(segment["brake"].mean()),
                full_throttle_pct=float((segment["throttle"] >= 0.98).mean() * 100.0),
                braking_frames_pct=float((segment["brake"] > 0.05).mean() * 100.0),
                drs_usage_pct=float(segment["drs"].mean() * 100.0),
            )
        )

    del status  # reserved for future ERS/fuel-aware analysis; unused for now

    return LapSummary(
        lap_number=lap.lap_number,
        lap_time=lap.lap_time,
        is_valid=lap.is_valid,
        sectors=(sectors[0], sectors[1], sectors[2]),
    )
