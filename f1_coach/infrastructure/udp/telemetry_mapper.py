"""TelemetryMapper — UDP structs → domain models.

This is the only place in the codebase that knows about UDP field names
(m_speed, m_throttle, m_ersStoreEnergy, etc.). Everything above this layer
works exclusively with domain types.

ERS store energy: the UDP field is in Joules (max ~4 000 000 J).
We normalise to a 0–100 percentage for the UI using the F1 25 max of 4 MJ.
"""

from dataclasses import dataclass

from f1_coach.domain.models.enums import SessionType, TrackName, WeatherCondition
from f1_coach.domain.models.telemetry_point import CarStatusPoint, TelemetryPoint
from f1_coach.infrastructure.udp.packets import (
    CarMotionData,
    CarStatusData,
    CarTelemetryData,
    LapData,
    PacketHeader,
    PacketSessionData,
)

_ERS_MAX_JOULES = 4_000_000.0

# Safety car status raw values (PacketSessionData.m_safetyCarStatus)
_SAFETY_CAR_NONE = 0


@dataclass(frozen=True, slots=True)
class SessionConditions:
    """Per-lap environmental snapshot, sampled from the latest Session packet.

    Weather and safety car status can change mid-session, so this is
    re-sampled at every lap completion rather than fixed once at session start.
    """

    weather: WeatherCondition
    safety_car_active: bool
    track_temperature: int
    air_temperature: int


@dataclass(frozen=True, slots=True)
class AssistConfig:
    """Session-level assist configuration, sampled once when the session starts.

    Player settings — do not change mid-session, unlike SessionConditions.
    """

    steering_assist: bool
    braking_assist: int
    gearbox_assist: int
    ers_assist: bool
    drs_assist: bool
    dynamic_racing_line: int
    corner_cutting_stringency: int

def map_car_position(car: CarMotionData) -> tuple[float, float]:
    """Motion paketinden aracın dünya koordinatlarındaki (X, Z) konumunu çıkarır.

    Y ekseni yükseklik (dikey) olduğu için 2D pist haritası için kullanılmaz —
    yalnızca X/Z düzlemi pist düzlemine karşılık gelir.
    """
    return float(car.m_worldPositionX), float(car.m_worldPositionZ)

def map_session_info(packet: PacketSessionData) -> tuple[str, TrackName, SessionType]:
    """Extract session UID, track and session type from a Session packet.

    Returns:
        (session_uid_hex, TrackName, SessionType)
    """
    uid_hex = format(packet.m_header.m_sessionUID, "016x")
    track = TrackName.from_udp(packet.m_trackId)
    session_type = SessionType.from_udp(packet.m_sessionType)
    return uid_hex, track, session_type


def map_session_conditions(packet: PacketSessionData) -> SessionConditions:
    """Extract the current environmental snapshot from a Session packet.

    Called on every incoming Session packet so SessionManager always holds
    the latest weather/safety-car/temperature state to sample at lap end.
    """
    return SessionConditions(
        weather=WeatherCondition.from_udp(packet.m_weather),
        safety_car_active=packet.m_safetyCarStatus != _SAFETY_CAR_NONE,
        track_temperature=int(packet.m_trackTemperature),
        air_temperature=int(packet.m_airTemperature),
    )


def map_assist_config(packet: PacketSessionData) -> AssistConfig:
    """Extract the assist configuration from a Session packet.

    Called once when a new session is detected — assists are a player
    setting and do not change mid-session.
    """
    return AssistConfig(
        steering_assist=bool(packet.m_steeringAssist),
        braking_assist=int(packet.m_brakingAssist),
        gearbox_assist=int(packet.m_gearboxAssist),
        ers_assist=bool(packet.m_ERSAssist),
        drs_assist=bool(packet.m_DRSAssist),
        dynamic_racing_line=int(packet.m_dynamicRacingLine),
        corner_cutting_stringency=int(packet.m_cornerCuttingStringency),
    )


def map_telemetry_point(
    header: PacketHeader,
    car: CarTelemetryData,
    track_position: float,
) -> TelemetryPoint:
    """Convert one CarTelemetryData frame to a TelemetryPoint.

    Args:
        header:         The packet header (provides session timestamp).
        car:            The per-car telemetry struct for the player's car.
        track_position: Normalised lap distance (0.0–1.0) sourced from
                        the concurrent LapData packet.
    """
    return TelemetryPoint(
        timestamp=float(header.m_sessionTime),
        track_position=track_position,
        speed=float(car.m_speed),
        throttle=float(car.m_throttle),
        brake=float(car.m_brake),
        steering=float(car.m_steer),
        gear=int(car.m_gear),
        rpm=int(car.m_engineRPM),
        drs=bool(car.m_drs),
    )


def map_car_status_point(
    header: PacketHeader,
    car: CarStatusData,
    track_position: float,
) -> CarStatusPoint:
    """Convert one CarStatusData frame to a CarStatusPoint.

    Args:
        header:         The packet header (provides session timestamp).
        car:            The per-car status struct for the player's car.
        track_position: Normalised lap distance sourced from LapData.
    """
    ers_pct = min(100.0, (float(car.m_ersStoreEnergy) / _ERS_MAX_JOULES) * 100.0)
    return CarStatusPoint(
        timestamp=float(header.m_sessionTime),
        track_position=track_position,
        ers_store=ers_pct,
        ers_deploy_mode=int(car.m_ersDeployMode),
        fuel_remaining=float(car.m_fuelInTank),
        tyre_compound=int(car.m_actualTyreCompound),
    )


def map_lap_distance(lap_data: LapData, track_length: float) -> float:
    """Compute normalised track position (0.0–1.0) from raw lap distance.

    Args:
        lap_data:     The per-car LapData struct for the player's car.
        track_length: Track length in metres (from PacketSessionData.m_trackLength).

    Returns:
        Clamped float in [0.0, 1.0].
    """
    if track_length <= 0:
        return 0.0
    raw = float(lap_data.m_lapDistance)
    return max(0.0, min(1.0, raw / track_length))


def map_lap_validity(lap_data: LapData) -> bool:
    """Return True if the lap was NOT flagged as invalid by the game."""
    return lap_data.m_currentLapInvalid == 0


def map_sector_times(lap_data: LapData) -> tuple[float, float, float]:
    """Extract sector times in seconds from a LapData struct.

    Sector times are broadcast as minutes + milliseconds fields.
    """
    s1 = lap_data.m_sector1TimeMinutes * 60.0 + lap_data.m_sector1TimeInMS / 1000.0
    s2 = lap_data.m_sector2TimeMinutes * 60.0 + lap_data.m_sector2TimeInMS / 1000.0
    # Sector 3 is not broadcast directly — derived at lap end from total − s1 − s2
    s3 = 0.0
    return s1, s2, s3
