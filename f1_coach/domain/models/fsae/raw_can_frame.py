"""RawCanFrame domain model.

The unlabeled, uninterpreted output of reading a CAN log file. Carries
zero semantic meaning by design — a RawCanFrame doesn't know whether its
bytes represent tire temperature or a checksum. Interpretation only
happens once a ChannelMapping is applied (see application/channel_decoder.py).

Kept separate from VehicleTelemetryPoint on purpose: if a channel is
mislabeled, it can be corrected and re-decoded from these frames without
re-importing the original log file.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RawCanFrame:
    """One raw CAN bus frame, exactly as read from the log file.

    Attributes:
        can_id:    Arbitration ID of the CAN frame (e.g. 0x123).
        timestamp: Seconds since session start.
        data:      Raw payload bytes — no interpretation applied.
    """

    can_id: int
    timestamp: float
    data: bytes