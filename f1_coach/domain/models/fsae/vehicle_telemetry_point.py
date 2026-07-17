"""VehicleTelemetryPoint domain model.

Unlike F1 25's TelemetryPoint (a fixed-width struct with named fields like
speed/throttle/brake), FSAE vehicles have a variable, team-specific channel
set. So telemetry is stored "long" — one row per (timestamp, channel) pair
— rather than "wide". Chart code pivots out the channels it needs from this
long table at render time (see project decision on dynamic channel graphing).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VehicleTelemetryPoint:
    """One decoded signal reading at one point in time.

    Attributes:
        timestamp:    Seconds since session start.
        channel_name: User-assigned channel name from the ChannelMapping
                      used to decode it — NOT the raw CAN ID.
        value:        Decoded physical value (already scaled/offset).
    """

    timestamp: float
    channel_name: str
    value: float