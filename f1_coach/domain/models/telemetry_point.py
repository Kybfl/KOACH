"""Telemetry domain models for a single data frame.

TelemetryPoint  — sourced from UDP Packet ID 6 (Car Telemetry), produced every frame.
CarStatusPoint  — sourced from UDP Packet ID 7 (Car Status), produced every frame.

Both carry a ``track_position`` field (0.0–1.0) that is used by the presentation
layer to align the two streams on a shared x-axis without a database join.

These are *pure data objects*: no ORM concerns, no UDP field names, no third-party
imports. The infrastructure mapper is responsible for the translation.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TelemetryPoint:
    """One frame of car telemetry data.

    Attributes:
        timestamp:       Wall-clock offset in seconds from session start.
        track_position:  Normalised distance around the lap (0.0 = start/finish,
                         1.0 = just before start/finish). Used as the shared x-axis
                         for all charts.
        speed:           Vehicle speed in km/h.
        throttle:        Throttle application from 0.0 (none) to 1.0 (full).
        brake:           Brake application from 0.0 (none) to 1.0 (full).
        steering:        Steering input; -1.0 = full left, +1.0 = full right.
        gear:            Currently selected gear (0 = reverse, 1–8 = forward gears).
        rpm:             Engine revolutions per minute.
        drs:             True when DRS is open and active.
    """

    timestamp: float
    track_position: float
    speed: float
    throttle: float
    brake: float
    steering: float
    gear: int
    rpm: int
    drs: bool


@dataclass(frozen=True, slots=True)
class CarStatusPoint:
    """One frame of car status data.

    Attributes:
        timestamp:        Wall-clock offset in seconds from session start.
        track_position:   Normalised distance around the lap — mirrors
                          TelemetryPoint.track_position so the two streams
                          can be aligned at the presentation layer.
        ers_store:        Energy stored in the ERS battery, expressed as a
                          percentage (0.0–100.0).
        ers_deploy_mode:  ERS deployment mode integer as broadcast by UDP.
                          0 = none, 1 = medium, 2 = overtake, 3 = hotlap.
        fuel_remaining:   Fuel load remaining in kilograms.
        tyre_compound:    Tyre compound integer as broadcast by UDP.
                          16 = C1 … 20 = C5, 7 = inter, 8 = wet (F1 25 values).
    """

    timestamp: float
    track_position: float
    ers_store: float
    ers_deploy_mode: int
    fuel_remaining: float
    tyre_compound: int
