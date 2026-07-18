"""Parquet writer for FSAE vehicle telemetry data.

Two files per imported session, mirroring the raw/decoded split explained
in the project's earlier storage decision:
    data/vehicle_sessions/<session_identifier>/raw_can_frames.parquet
    data/vehicle_sessions/<session_identifier>/decoded_telemetry.parquet

Keeping raw frames on disk (not just the decoded result) is what lets a
mislabeled ChannelMapping be corrected and re-decoded without re-importing
the original CAN log file.

session_identifier is caller-generated (e.g. uuid4 hex) at import time,
since — unlike F1 25's UDP session_uid — there is no natural stable
identifier available before the VehicleSession is persisted to SQLite.
"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from f1_coach.domain.models.fsae.raw_can_frame import RawCanFrame
from f1_coach.domain.models.fsae.vehicle_telemetry_point import VehicleTelemetryPoint
from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path("data/vehicle_sessions")

_RAW_FILENAME = "raw_can_frames.parquet"
_DECODED_FILENAME = "decoded_telemetry.parquet"


def _session_dir(session_identifier: str) -> Path:
    path = _BASE_DIR / session_identifier
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_raw_can_frames(session_identifier: str, frames: list[RawCanFrame]) -> str:
    """Serialise raw CAN frames to a Parquet file, immediately after import.

    Args:
        session_identifier: Caller-generated unique identifier for this
                            import (see module docstring).
        frames:             All frames read by CanLogReader.read_frames().

    Returns:
        Absolute path of the written file as a string.

    Raises:
        ValueError: If ``frames`` is empty.
    """
    if not frames:
        raise ValueError("No CAN frames to write.")

    df = pd.DataFrame(
        {
            "can_id": [f.can_id for f in frames],
            "timestamp": [f.timestamp for f in frames],
            "data": [f.data for f in frames],
        }
    )

    output_path = _session_dir(session_identifier) / _RAW_FILENAME
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")

    logger.debug(
        "Raw CAN frames written: session=%s rows=%d path=%s",
        session_identifier, len(frames), output_path,
    )
    return str(output_path.resolve())


def write_decoded_telemetry(session_identifier: str, points: list[VehicleTelemetryPoint]) -> str:
    """Serialise decoded telemetry points to a Parquet file, after labeling.

    Called every time the user finishes (or corrects) labeling — this file
    is overwritten each time, since it's fully derived from raw_can_frames
    + the current ChannelMapping set, never hand-edited.

    Args:
        session_identifier: Same identifier used for write_raw_can_frames().
        points:              Output of application/fsae/channel_decoder.decode_telemetry().

    Returns:
        Absolute path of the written file as a string.

    Raises:
        ValueError: If ``points`` is empty.
    """
    if not points:
        raise ValueError("No decoded telemetry points to write.")

    df = pd.DataFrame(
        {
            "timestamp": [p.timestamp for p in points],
            "channel_name": [p.channel_name for p in points],
            "value": [p.value for p in points],
        }
    )

    output_path = _session_dir(session_identifier) / _DECODED_FILENAME
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")

    logger.debug(
        "Decoded telemetry written: session=%s rows=%d channels=%d path=%s",
        session_identifier, len(points), df["channel_name"].nunique(), output_path,
    )
    return str(output_path.resolve())


def read_raw_can_frames(file_path: str) -> pd.DataFrame:
    """Read a raw CAN frames Parquet file back into a DataFrame.

    Used when the user re-opens the Etiketleme screen or corrects a mapping.

    Returns:
        DataFrame with columns: can_id, timestamp, data (bytes).
    """
    return pq.read_table(file_path).to_pandas()


def read_decoded_telemetry(file_path: str) -> pd.DataFrame:
    """Read a decoded telemetry Parquet file back into a DataFrame.

    Used by the chart page to pivot out the channels the user selects.

    Returns:
        DataFrame with columns: timestamp, channel_name, value.
    """
    return pq.read_table(file_path).to_pandas()


def delete_session_files(session_identifier: str) -> None:
    """Delete the entire session directory tree from disk.

    Called by the application layer when a VehicleSession is deleted via the UI.
    """
    import shutil

    session_dir = _BASE_DIR / session_identifier
    if session_dir.exists():
        shutil.rmtree(session_dir)
        logger.info("Deleted vehicle session directory: %s", session_dir)

def raw_can_frames_from_dataframe(df: pd.DataFrame) -> list[RawCanFrame]:
    """Convert a raw CAN frames DataFrame (as read by read_raw_can_frames)
    back into RawCanFrame domain objects.

    Used when re-decoding after a labeling correction — the original CAN
    log file is never re-read, only this Parquet file.
    """
    return [
        RawCanFrame(can_id=int(row.can_id), timestamp=float(row.timestamp), data=bytes(row.data))
        for row in df.itertuples(index=False)
    ]