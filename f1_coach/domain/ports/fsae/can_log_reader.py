"""CanLogReader port — the boundary between the application and raw CAN log files.

Concrete implementations live in infrastructure/can/ and wrap a specific
parsing library (e.g. python-can's LogReader) to support the range of raw
log formats FSAE dataloggers export (.blf, .asc, .trc, ...). The application
layer never inspects the file format directly — it only ever calls
read_frames() and works with RawCanFrame from there on.
"""

from typing import Protocol

from f1_coach.domain.models.fsae.raw_can_frame import RawCanFrame


class CanLogReader(Protocol):
    """Contract for raw CAN log file readers."""

    def read_frames(self, file_path: str) -> list[RawCanFrame]:
        """Parse a raw CAN log file into a list of RawCanFrame.

        No signal decoding happens here — frames are returned exactly as
        read, carrying only CAN ID, timestamp, and raw payload bytes.
        Interpretation is applied later via ChannelMapping (see
        application/fsae/channel_decoder.py).

        Args:
            file_path: Absolute path to the raw CAN log file.

        Returns:
            All frames in the file, ordered by timestamp ascending.

        Raises:
            ValueError: If the file format is unrecognised or unreadable.
        """
        ...