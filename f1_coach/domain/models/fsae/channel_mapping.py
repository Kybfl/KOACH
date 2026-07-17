"""ChannelMapping domain model.

User-defined interpretation of a byte range within a CAN ID's payload —
the manual, in-app equivalent of a DBC signal definition. Different FSAE
vehicles use completely different CAN ID assignments, so KOACH does not
ship or infer any mapping; the user labels each CAN ID they care about via
the Etiketleme screen. Mappings are session-scoped and are NOT reused
across sessions (project decision — re-labeling is expected each import).

One CAN ID can carry multiple signals (e.g. byte 0-1 = front-left wheel
speed, byte 2-3 = front-right wheel speed within the same frame), so a
session can have several ChannelMapping rows sharing the same can_id.
"""

from dataclasses import dataclass, field


@dataclass
class ChannelMapping:
    """One labeled signal within a CAN ID's payload.

    Attributes:
        session_id:    Foreign key to the parent VehicleSession.
        can_id:        Arbitration ID this signal is extracted from.

        start_byte:   Byte offset within the payload where the signal starts.
                      Signals must be byte-aligned — sub-byte bit offsets
                      within a byte (e.g. two 4-bit values packed into one
                      byte) are NOT supported. If a mapping needs that, split
                      the byte manually is not possible here; this is a
                      known, accepted limitation for now.

        bit_length:   Signal width in bits, extracted starting at start_byte.
                      Does not need to be a multiple of 8 (e.g. 12 bits is
                      fine), but always starts reading from a full byte
                      boundary — never from a bit offset within start_byte.
                      
        little_endian: True if little-endian (Intel), False if big-endian
                       (Motorola) byte order.
        signed:        True if the raw integer is two's-complement signed.
        scale:         physical_value = raw_value * scale + offset.
        offset:        Linear offset, applied after scaling.
        name:          User-assigned channel name (e.g. "on_sol_tekerlek_hizi").
        unit:          User-assigned unit label (e.g. "km/s"), display-only.
        id:            Database primary key; -1 means not yet persisted.
    """

    session_id: int
    can_id: int
    start_byte: int
    bit_length: int
    little_endian: bool
    signed: bool
    scale: float
    offset: float
    name: str
    unit: str
    id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1