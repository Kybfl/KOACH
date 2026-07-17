"""UDP packet parsers.

Each parser receives the raw bytes of a full UDP datagram and returns a
typed ctypes struct. The caller (TelemetryReceiver) is responsible for
reading m_packetId from the header before dispatching to the right parser.

All parsers return None on malformed input so the receiver can skip
corrupt datagrams gracefully without crashing the capture loop.
"""

import ctypes

from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.f125_udp.packets import (
    PacketCarSetupData,      
    PacketCarStatusData,
    PacketCarTelemetryData,
    PacketHeader,
    PacketLapData,
    PacketMotionData,
    PacketSessionData,
)

logger = get_logger(__name__)


def parse_header(data: bytes) -> PacketHeader | None:
    """Parse just the packet header to determine packet type."""
    try:
        return PacketHeader.from_buffer_copy(data)
    except Exception as exc:
        logger.debug("Header parse failed: %s", exc)
        return None


def _parse(struct_type: type, data: bytes):
    """Generic struct parser with error handling."""
    expected = ctypes.sizeof(struct_type)
    if len(data) < expected:
        logger.debug(
            "Packet too short: got %d bytes, expected %d for %s",
            len(data),
            expected,
            struct_type.__name__,
        )
        return None
    try:
        return struct_type.from_buffer_copy(data)
    except Exception as exc:
        logger.debug("Parse error for %s: %s", struct_type.__name__, exc)
        return None

def parse_motion(data: bytes) -> PacketMotionData | None:
    """Parse Packet ID 0 — Motion Data."""
    return _parse(PacketMotionData, data)

def parse_session(data: bytes) -> PacketSessionData | None:
    """Parse Packet ID 1 — Session Data."""
    return _parse(PacketSessionData, data)


def parse_lap_data(data: bytes) -> PacketLapData | None:
    """Parse Packet ID 2 — Lap Data."""
    return _parse(PacketLapData, data)


def parse_car_telemetry(data: bytes) -> PacketCarTelemetryData | None:
    """Parse Packet ID 6 — Car Telemetry."""
    return _parse(PacketCarTelemetryData, data)


def parse_car_status(data: bytes) -> PacketCarStatusData | None:
    """Parse Packet ID 7 — Car Status."""
    return _parse(PacketCarStatusData, data)

def parse_car_setup(data: bytes) -> PacketCarSetupData | None:
    """Parse Packet ID 5 — Car Setups."""
    return _parse(PacketCarSetupData, data)