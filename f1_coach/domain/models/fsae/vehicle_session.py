"""VehicleSession domain model.

Represents one imported CAN log file from a Formula Student vehicle's
datalogger, collected post-run via USB. Distinct from KOACH's F1 25
Session model — there is no lap concept yet (GPS-based lap detection
is a possible future extension), so this groups raw + decoded telemetry
as a single flat session rather than a collection of laps.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VehicleSession:
    """One imported CAN log session from the FSAE vehicle's datalogger.

    Attributes:
        name:                   User-provided label for this session
                                (e.g. "Endurance - 14.07.2026").
        source_filename:        Original filename of the imported raw CAN
                                log, kept for traceability only — never
                                re-parsed from this value directly.
        raw_can_file:           Absolute path to the raw CAN frames Parquet
                                file (RawCanFrame rows), written at import.
        decoded_telemetry_file: Absolute path to the decoded telemetry
                                Parquet file (VehicleTelemetryPoint rows),
                                written once labeling completes. Empty
                                string until then.
        imported_at:            When this session was imported into KOACH.
        id:                     Database primary key; -1 means not yet persisted.
    """

    name: str
    source_filename: str
    raw_can_file: str
    decoded_telemetry_file: str = field(default="")
    imported_at: datetime = field(default_factory=datetime.now)
    id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1

    @property
    def is_labeled(self) -> bool:
        """True once at least one channel mapping has been decoded and saved."""
        return bool(self.decoded_telemetry_file)