"""Parquet writer for raw telemetry data.

Each lap gets two Parquet files:
    data/sessions/<session_uid>/laps/lap_<N>_telemetry.parquet
    data/sessions/<session_uid>/laps/lap_<N>_status.parquet

File paths are returned so they can be stored in the Lap domain model and
persisted to SQLite by the caller (application layer).

Why Parquet?
    ~60 packets/second × 90-second lap = ~5 400 rows per lap.
    Parquet's columnar compression keeps each file well under 1 MB while
    enabling fast column-oriented reads for chart rendering.
"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from f1_coach.domain.models.f125.telemetry_point import CarStatusPoint, TelemetryPoint
from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path("data/sessions")


def _lap_dir(session_uid: str) -> Path:
    path = _BASE_DIR / session_uid / "laps"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_telemetry(
    session_uid: str,
    lap_number: int,
    points: list[TelemetryPoint],
) -> str:
    """Serialise a list of TelemetryPoint frames to a Parquet file.

    Args:
        session_uid: The UDP session UID string (used as the directory name).
        lap_number:  1-based lap number.
        points:      All TelemetryPoint frames captured during the lap.

    Returns:
        Absolute path of the written file as a string.

    Raises:
        ValueError: If ``points`` is empty.
    """
    if not points:
        raise ValueError(f"No telemetry points to write for lap {lap_number}.")

    df = pd.DataFrame(
        {
            "timestamp": [p.timestamp for p in points],
            "track_position": [p.track_position for p in points],
            "speed": [p.speed for p in points],
            "throttle": [p.throttle for p in points],
            "brake": [p.brake for p in points],
            "steering": [p.steering for p in points],
            "gear": [p.gear for p in points],
            "rpm": [p.rpm for p in points],
            "drs": [p.drs for p in points],
        }
    )

    output_path = _lap_dir(session_uid) / f"lap_{lap_number:03d}_telemetry.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")

    logger.debug(
        "Telemetry written: session=%s lap=%d rows=%d path=%s",
        session_uid,
        lap_number,
        len(points),
        output_path,
    )
    return str(output_path.resolve())


def write_car_status(
    session_uid: str,
    lap_number: int,
    points: list[CarStatusPoint],
) -> str:
    """Serialise a list of CarStatusPoint frames to a Parquet file.

    Args:
        session_uid: The UDP session UID string.
        lap_number:  1-based lap number.
        points:      All CarStatusPoint frames captured during the lap.

    Returns:
        Absolute path of the written file as a string.

    Raises:
        ValueError: If ``points`` is empty.
    """
    if not points:
        raise ValueError(f"No car status points to write for lap {lap_number}.")

    df = pd.DataFrame(
        {
            "timestamp": [p.timestamp for p in points],
            "track_position": [p.track_position for p in points],
            "ers_store": [p.ers_store for p in points],
            "ers_deploy_mode": [p.ers_deploy_mode for p in points],
            "fuel_remaining": [p.fuel_remaining for p in points],
            "tyre_compound": [p.tyre_compound for p in points],
        }
    )

    output_path = _lap_dir(session_uid) / f"lap_{lap_number:03d}_status.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")

    logger.debug(
        "Car status written: session=%s lap=%d rows=%d path=%s",
        session_uid,
        lap_number,
        len(points),
        output_path,
    )
    return str(output_path.resolve())

def write_positions(
    session_uid: str,
    lap_number: int,
    positions: list[tuple[float, float, float]],
) -> str:
    """Bir turun pist üzerindeki (track_position, x, z) noktalarını Parquet'e yazar.

    Args:
        session_uid: UDP session UID string.
        lap_number:  1-tabanlı tur numarası.
        positions:   (track_position, pos_x, pos_z) üçlülerinin listesi.

    Returns:
        Yazılan dosyanın mutlak yolu.

    Raises:
        ValueError: positions boşsa.
    """
    if not positions:
        raise ValueError(f"No position points to write for lap {lap_number}.")

    df = pd.DataFrame(positions, columns=["track_position", "pos_x", "pos_z"])

    output_path = _lap_dir(session_uid) / f"lap_{lap_number:03d}_positions.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")

    logger.debug(
        "Positions written: session=%s lap=%d rows=%d path=%s",
        session_uid, lap_number, len(positions), output_path,
    )
    return str(output_path.resolve())


def read_positions(file_path: str) -> pd.DataFrame:
    """Bir pozisyon Parquet dosyasını DataFrame olarak okur.

    Args:
        file_path: Parquet dosyasının yolu.

    Returns:
        track_position, pos_x, pos_z kolonlarını içeren DataFrame.
    """
    return pq.read_table(file_path).to_pandas()

def read_telemetry(file_path: str) -> pd.DataFrame:
    """Read a telemetry Parquet file back into a DataFrame.

    Used by the presentation layer when rendering charts.

    Args:
        file_path: Absolute or relative path to the Parquet file.

    Returns:
        DataFrame with columns: timestamp, track_position, speed, throttle,
        brake, steering, gear, rpm, drs.
    """
    return pq.read_table(file_path).to_pandas()


def read_car_status(file_path: str) -> pd.DataFrame:
    """Read a car status Parquet file back into a DataFrame.

    Args:
        file_path: Absolute or relative path to the Parquet file.

    Returns:
        DataFrame with columns: timestamp, track_position, ers_store,
        ers_deploy_mode, fuel_remaining, tyre_compound.
    """
    return pq.read_table(file_path).to_pandas()


def delete_lap_files(session_uid: str, lap_number: int) -> None:
    """Delete both Parquet files for a lap if they exist.

    Called by the application layer when a session is deleted.
    """
    lap_d = _lap_dir(session_uid)
    for suffix in ("telemetry", "status"):
        path = lap_d / f"lap_{lap_number:03d}_{suffix}.parquet"
        if path.exists():
            path.unlink()
            logger.debug("Deleted parquet file: %s", path)


def delete_session_files(session_uid: str) -> None:
    """Delete the entire session directory tree from disk.

    Called by the application layer when a session is deleted via the UI.
    """
    import shutil

    session_dir = _BASE_DIR / session_uid
    if session_dir.exists():
        shutil.rmtree(session_dir)
        logger.info("Deleted session directory: %s", session_dir)
