"""python-can-based CanLogReader implementation.

Wraps can.LogReader, which auto-detects the raw log format from the file
extension (.asc, .blf, .csv, .db, .log, .trc, and .mf4 if the optional
asammdf dependency is installed) and yields can.Message objects. See:
https://python-can.readthedocs.io/en/stable/file_io.html

Timestamps in python-can logs follow whatever convention the source format
used (some are wall-clock epoch seconds, some are already relative to
capture start). RawCanFrame's contract is "seconds since session start",
so timestamps are normalised here by subtracting the first frame's raw
timestamp — this keeps the output consistent regardless of which log
format was read.
"""

import fsae_can

from f1_coach.domain.models.fsae.raw_can_frame import RawCanFrame
from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class PythonCanLogReader:
    """CanLogReader implementation backed by python-can's format-agnostic LogReader."""

    def read_frames(self, file_path: str) -> list[RawCanFrame]:
        """Parse a raw CAN log file into a list of RawCanFrame.

        Raises:
            ValueError: If the file suffix is unrecognised, a required
                        optional dependency for that format isn't installed
                        (e.g. asammdf for .mf4), or the file can't be parsed.
        """
        try:
            reader = fsae_can.LogReader(file_path)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Could not open CAN log file '{file_path}': {exc}") from exc

        frames: list[RawCanFrame] = []
        first_timestamp: float | None = None
        skipped_error_frames = 0

        try:
            for msg in reader:
                if msg.is_error_frame:
                    skipped_error_frames += 1
                    continue

                if first_timestamp is None:
                    first_timestamp = msg.timestamp

                frames.append(
                    RawCanFrame(
                        can_id=msg.arbitration_id,
                        timestamp=msg.timestamp - first_timestamp,
                        data=bytes(msg.data),
                    )
                )
        except Exception as exc:
            raise ValueError(f"Failed while reading CAN log file '{file_path}': {exc}") from exc
        finally:
            if hasattr(reader, "stop"):
                reader.stop()

        if not frames:
            raise ValueError(f"CAN log file '{file_path}' contained no readable data frames.")

        if skipped_error_frames:
            logger.info(
                "Skipped %d error frame(s) while reading '%s'.",
                skipped_error_frames, file_path,
            )

        logger.info(
            "Read %d CAN frames (%d distinct IDs) from '%s'.",
            len(frames), len({f.can_id for f in frames}), file_path,
        )
        return frames