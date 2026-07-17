"""channel_decoder — applies user-defined ChannelMapping rules to RawCanFrame data.

This is the FSAE module's counterpart to F1 25's telemetry_mapper.py: the
only place that turns "meaningless bytes" into "meaningful physical values".
Pure function, no I/O — reading frames/mappings and writing the result are
both the caller's responsibility (see fsae_import_page.py once we get there).

Decoding is intentionally forgiving: a malformed or out-of-range mapping for
a given frame is skipped with a warning rather than raising, since a single
mislabeled channel should not prevent the rest of the session from decoding.
"""

from collections import defaultdict

from f1_coach.domain.models.fsae.channel_mapping import ChannelMapping
from f1_coach.domain.models.fsae.raw_can_frame import RawCanFrame
from f1_coach.domain.models.fsae.vehicle_telemetry_point import VehicleTelemetryPoint
from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


def _extract_raw_value(data: bytes, start_byte: int, bit_length: int, little_endian: bool) -> int:
    """Pull bit_length bits out of data starting at start_byte as an unsigned int.

    Only byte-level start offsets are supported (no sub-byte bit offset) —
    matches ChannelMapping's fields. If bit_length isn't a multiple of 8,
    the value is masked to its low bit_length bits after byte extraction.
    """
    num_bytes = (bit_length + 7) // 8
    end_byte = start_byte + num_bytes
    if start_byte < 0 or end_byte > len(data):
        raise ValueError(
            f"Mapping expects bytes [{start_byte}:{end_byte}) but frame only has {len(data)} bytes."
        )
    chunk = data[start_byte:end_byte]
    raw = int.from_bytes(chunk, byteorder="little" if little_endian else "big")
    if bit_length % 8 != 0:
        raw &= (1 << bit_length) - 1
    return raw


def _to_signed(raw: int, bit_length: int) -> int:
    """Reinterpret an unsigned bit_length-bit integer as two's-complement signed."""
    sign_bit = 1 << (bit_length - 1)
    return raw - (1 << bit_length) if raw & sign_bit else raw


def _decode_one(
    frame: RawCanFrame,
    mapping: ChannelMapping,
    warned_mapping_ids: set[int],
) -> VehicleTelemetryPoint | None:
    """Decode a single (frame, mapping) pair, or None if the frame doesn't fit."""
    try:
        raw = _extract_raw_value(frame.data, mapping.start_byte, mapping.bit_length, mapping.little_endian)
    except ValueError as exc:
        if id(mapping) not in warned_mapping_ids:
            logger.warning(
                "Skipping frames for channel '%s' (can_id=0x%X): %s "
                "(further mismatches for this channel will be silenced this session)",
                mapping.name, mapping.can_id, exc,
            )
            warned_mapping_ids.add(id(mapping))
        return None

    if mapping.signed:
        raw = _to_signed(raw, mapping.bit_length)

    value = raw * mapping.scale + mapping.offset
    return VehicleTelemetryPoint(
        timestamp=frame.timestamp,
        channel_name=mapping.name,
        value=value,
    )


def decode_telemetry(
    frames: list[RawCanFrame],
    mappings: list[ChannelMapping],
) -> list[VehicleTelemetryPoint]:
    """Decode raw CAN frames into VehicleTelemetryPoint rows using the given mappings.

    A single CAN ID may have multiple mappings (multiple signals packed into
    one frame — see ChannelMapping's docstring), so every matching mapping is
    applied to every frame sharing that can_id.

    Args:
        frames:   Raw frames, expected in the timestamp-ascending order that
                  CanLogReader.read_frames() guarantees. Decoding still works
                  on out-of-order input, but downstream chart rendering
                  assumes ascending timestamps per channel, so out-of-order
                  input should be avoided rather than relied upon.
        mappings: User-defined mappings for this session (see ChannelMappingRepository).

    Returns:
        Decoded points, in the same relative order as the input frames.
        CAN IDs with no matching mapping are silently ignored — this is
        expected (e.g. checksum/heartbeat frames the user chose not to label).
    """
    mappings_by_id: dict[int, list[ChannelMapping]] = defaultdict(list)
    for mapping in mappings:
        mappings_by_id[mapping.can_id].append(mapping)

    warned_mapping_ids: set[int] = set()
    points: list[VehicleTelemetryPoint] = []
    for frame in frames:
        for mapping in mappings_by_id.get(frame.can_id, []):
            point = _decode_one(frame, mapping, warned_mapping_ids)
            if point is not None:
                points.append(point)

    logger.info(
        "Decoded %d telemetry points from %d frames using %d mappings.",
        len(points), len(frames), len(mappings),
    )
    return points