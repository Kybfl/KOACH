"""Lap domain model.

A Lap represents one completed circuit of the track within a Session.
Sector times and validity come directly from the UDP stream (Packet ID 2).
File paths point to the Parquet files written by the storage layer.

Weather, safety car status, and track/air temperature are captured per-lap
(not per-session) because these conditions can change mid-session — for
example rain starting during a race. A session-level field would silently
misattribute conditions to laps driven before/after a transition.
"""

from dataclasses import dataclass, field

from f1_coach.domain.models.enums import WeatherCondition


@dataclass
class Lap:
    """A single completed lap.

    Attributes:
        lap_number:         1-based lap number within the session.
        lap_time:            Total lap duration in seconds.
        sector_1_time:       Sector 1 duration in seconds.
        sector_2_time:       Sector 2 duration in seconds.
        sector_3_time:       Sector 3 duration in seconds.
        
        is_valid:            False if a track-limit violation was detected by the
                             game. Invalid laps are excluded from AI analysis and
                             best-lap logic.
        
        tyre_compound:       Tyre compound integer for this lap (raw UDP value).
        
        weather:             Weather condition sampled when the lap completed.
        
        safety_car_active:   True if a safety car, VSC, or formation lap was
                             active at any point during this lap. Excluded from
                             best-lap reference selection like invalid laps —
                             an artificially slow SC lap cannot be a legitimate
                             reference time.
        
        track_temperature:   Track temperature in Celsius, sampled at lap end.
        
        air_temperature:     Air temperature in Celsius, sampled at lap end.
        
        telemetry_file:      Absolute path to the TelemetryPoint Parquet file.
                             Empty string if the file has not been written yet.
        
        status_file:         Absolute path to the CarStatusPoint Parquet file.
                             Empty string if the file has not been written yet.
        
        position_file:       Absolute path to the (track_position, x, z) Parquet file
                             used for track map visualisation. Empty string if not
                             captured (e.g. Motion packet never received).
        
        id:                  Database primary key; -1 means not yet persisted.
        
        session_id:          Foreign key to the parent Session; -1 means not yet set.
    """

    lap_number: int
    lap_time: float
    sector_1_time: float
    sector_2_time: float
    sector_3_time: float
    is_valid: bool
    tyre_compound: int
    weather: WeatherCondition = field(default=WeatherCondition.CLEAR)
    safety_car_active: bool = field(default=False)
    track_temperature: int = field(default=0)
    air_temperature: int = field(default=0)
    telemetry_file: str = field(default="")
    status_file: str = field(default="")
    status_file: str = field(default="")
    position_file: str = field(default="")
    id: int = field(default=-1)
    session_id: int = field(default=-1)

    @property
    def sector_times(self) -> tuple[float, float, float]:
        """Convenience accessor for all three sector times as a tuple."""
        return self.sector_1_time, self.sector_2_time, self.sector_3_time

    @property
    def is_persisted(self) -> bool:
        """True when this lap has been saved to the database."""
        return self.id != -1

    @property
    def is_valid_reference(self) -> bool:
        """True if this lap can legitimately serve as a best-lap reference.

        Combines track-limit validity with safety-car exclusion — both
        conditions must hold for a lap's time to be a fair comparison point.
        """
        return self.is_valid and not self.safety_car_active
