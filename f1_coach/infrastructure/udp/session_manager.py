"""SessionManager — session and lap lifecycle management.

Responsibilities:
  - Create a new Session when a new session UID is detected
  - Accumulate TelemetryPoint and CarStatusPoint frames per lap
  - Detect lap completion (lap number increment in LapData)
  - Write Parquet files and persist the completed lap to SQLite
  - Expose the current session for the UI to read

This class is synchronous and stateful. It is owned by TelemetryReceiver
and called from the capture loop on every relevant packet.
"""

from datetime import datetime

from f1_coach.domain.models.car_setup import CarSetup
from f1_coach.domain.ports.car_setup_repository import CarSetupRepository
from f1_coach.infrastructure.udp.telemetry_mapper import AssistConfig, CarSetupFields, SessionConditions
from f1_coach.domain.models.enums import SessionType, TrackName, WeatherCondition
from f1_coach.domain.models.lap import Lap
from f1_coach.domain.models.session import Session
from f1_coach.domain.models.telemetry_point import CarStatusPoint, TelemetryPoint
from f1_coach.domain.ports.lap_repository import LapRepository
from f1_coach.domain.ports.session_repository import SessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.parquet_writer import write_car_status, write_telemetry
from f1_coach.infrastructure.udp.telemetry_mapper import AssistConfig, SessionConditions
from f1_coach.infrastructure.storage.parquet_writer import (
    write_car_status,
    write_positions,
    write_telemetry,
)

logger = get_logger(__name__)

# fuel_load kasıtlı olarak dışarıda bırakıldı — her turda yakıt azaldığı için
# karşılaştırmaya dahil edilirse her lap'te "yeni setup" algılanır.
_SETUP_COMPARISON_FIELDS = (
    "front_wing", "rear_wing", "on_throttle_diff", "off_throttle_diff",
    "front_camber", "rear_camber", "front_toe", "rear_toe",
    "front_suspension", "rear_suspension", "front_arb", "rear_arb",
    "front_ride_height", "rear_ride_height",
    "brake_pressure", "brake_bias",
    "front_left_tyre_pressure", "front_right_tyre_pressure",
    "rear_left_tyre_pressure", "rear_right_tyre_pressure",
    "ballast",
)


def _setup_fields_changed(a: CarSetupFields, b: CarSetupFields) -> bool:
    """True if any tunable setup value differs — fuel_load excluded (see above)."""
    return any(getattr(a, f) != getattr(b, f) for f in _SETUP_COMPARISON_FIELDS)

class SessionManager:
    """Owns the current session and handles lap transitions."""

    def __init__(
    self,
    session_repo: SessionRepository,
    lap_repo: LapRepository,
    car_setup_repo: CarSetupRepository,   # ← yeni parametre
    ) -> None:
        self._session_repo = session_repo
        self._lap_repo = lap_repo
        self._car_setup_repo = car_setup_repo   # ← yeni satır
        
        self._last_setup_fields: CarSetupFields | None = None
        self._session: Session | None = None
        self._track_length: float = 0.0

        # Per-lap accumulators
        self._telemetry_buffer: list[TelemetryPoint] = []
        self._latest_telemetry: TelemetryPoint | None = None
        self._latest_telemetry: TelemetryPoint | None = None
        self._current_lap_positions: list[tuple[float, float]] = []
        self._status_buffer: list[CarStatusPoint] = []
        self._current_lap_number: int = 0
        self._current_lap_invalid: bool = False
        self._current_lap_safety_car: bool = False
        self._last_sector_times: tuple[float, float, float] = (0.0, 0.0, 0.0)

        # Latest environmental snapshot, updated on every Session packet.
        # Sampled into the Lap object at the moment each lap is finalised.
        self._latest_conditions = SessionConditions(
            weather=WeatherCondition.CLEAR,
            safety_car_active=False,
            track_temperature=0,
            air_temperature=0,
        )

    # ------------------------------------------------------------------
    # Public interface — called by TelemetryReceiver
    # ------------------------------------------------------------------

    @property
    def current_session(self) -> Session | None:
        return self._session

    @property
    def latest_telemetry(self) -> TelemetryPoint | None:
        """En son alınan telemetri karesi — Canlı Session ekranındaki anlık
        hız/gaz/RPM göstergeleri için kullanılır. Hiç veri gelmediyse None."""
        return self._latest_telemetry

    def on_car_position(self, x: float, z: float, track_position: float) -> None:
        """Motion paketinden gelen (X, Z) konumunu, pist pozisyonuyla birlikte
        mevcut tur için biriktirir. track_position, Lap Analizi'nde bu noktaları
        telemetri (hız) verisiyle eşleştirmek için kullanılır.
        """
        if self._session is not None and self._current_lap_number > 0:
            self._current_lap_positions.append((track_position, x, z))

    def on_session_packet(
        self,
        session_uid: str,
        track: TrackName,
        session_type: SessionType,
        track_length: float,
        assist_config: AssistConfig,
    ) -> None:
        """Handle an incoming Session packet (Packet ID 1).

        Creates a new session if the UID has changed. Assist configuration is
        captured only at session start — it is a player setting that does not
        change mid-session.
        """
        if self._session is not None and self._session.session_uid == session_uid:
            return  # same session, nothing to do

        logger.info(
            "New session detected: uid=%s track=%s type=%s",
            session_uid,
            track.display_name,
            session_type.display_name,
        )
        self._flush_current_lap()  # save any in-progress lap from previous session
        self._start_session(session_uid, track, session_type, assist_config)
        self._track_length = track_length

    def on_session_conditions(self, conditions: SessionConditions) -> None:
        """Update the latest environmental snapshot (weather, safety car, temps).

        Called on every incoming Session packet. Also tracks whether a safety
        car/VSC/formation lap was active at any point during the current lap
        — once triggered, that flag stays set for the rest of the lap, just
        like the existing invalid-lap tracking.
        """
        self._latest_conditions = conditions
        if conditions.safety_car_active:
            self._current_lap_safety_car = True

    def on_car_setup_packet(self, fields: CarSetupFields) -> None:
        """Handle an incoming Car Setup packet (Packet ID 5).

        The broadcast repeats every frame even when the setup hasn't changed —
        only persists a new CarSetup row when the tunable values actually
        differ from the last one seen, turning a continuous stream into
        discrete "setup changed" events (e.g. after a pit stop).
        """
        if self._session is None:
            return

        if self._last_setup_fields is not None and not _setup_fields_changed(
            fields, self._last_setup_fields
        ):
            return  # aynı setup, kayıt gerekmiyor

        self._last_setup_fields = fields

        setup = CarSetup(
            session_id=self._session.id,
            valid_from_lap=max(1, self._current_lap_number),
            front_wing=fields.front_wing,
            rear_wing=fields.rear_wing,
            on_throttle_diff=fields.on_throttle_diff,
            off_throttle_diff=fields.off_throttle_diff,
            front_camber=fields.front_camber,
            rear_camber=fields.rear_camber,
            front_toe=fields.front_toe,
            rear_toe=fields.rear_toe,
            front_suspension=fields.front_suspension,
            rear_suspension=fields.rear_suspension,
            front_arb=fields.front_arb,
            rear_arb=fields.rear_arb,
            front_ride_height=fields.front_ride_height,
            rear_ride_height=fields.rear_ride_height,
            brake_pressure=fields.brake_pressure,
            brake_bias=fields.brake_bias,
            front_left_tyre_pressure=fields.front_left_tyre_pressure,
            front_right_tyre_pressure=fields.front_right_tyre_pressure,
            rear_left_tyre_pressure=fields.rear_left_tyre_pressure,
            rear_right_tyre_pressure=fields.rear_right_tyre_pressure,
            ballast=fields.ballast,
            fuel_load=fields.fuel_load,
        )
        self._car_setup_repo.save(setup)

        logger.info(
            "New car setup detected: session=%s valid_from_lap=%d",
            self._session.session_uid, setup.valid_from_lap,
        )

    def on_lap_packet(
        self,
        lap_number: int,
        lap_time_ms: int,
        sector_times: tuple[float, float, float],
        is_valid: bool,
        tyre_compound: int,
    ) -> None:
        """Handle an incoming Lap Data packet (Packet ID 2).

        Detects lap number transitions and finalises the previous lap.
        """
        if self._session is None:
            return

        if lap_number != self._current_lap_number:
            if self._current_lap_number > 0:
                self._finalise_lap(lap_time_ms, tyre_compound)
            self._current_lap_number = lap_number
            self._current_lap_invalid = False
            self._current_lap_safety_car = False
            logger.debug("Lap transition → lap %d", lap_number)

        # Track validity degradation (once invalid, stays invalid for this lap)
        if not is_valid:
            self._current_lap_invalid = True

        self._last_sector_times = sector_times

    def on_telemetry_point(self, point: TelemetryPoint) -> None:
        """Buffer a TelemetryPoint frame for the current lap and track latest.

        latest_telemetry is updated unconditionally (even between laps, e.g.
        in the pit lane) so the live UI can always show current speed/gear/rpm.
        """
        self._latest_telemetry = point
        if self._session is not None and self._current_lap_number > 0:
            self._telemetry_buffer.append(point)

    def on_car_status_point(self, point: CarStatusPoint) -> None:
        """Buffer a CarStatusPoint frame for the current lap."""
        if self._session is not None and self._current_lap_number > 0:
            self._status_buffer.append(point)

    def end_session(self) -> None:
        """Manually end the current session (triggered by the UI button)."""
        logger.info("Session ended manually by user.")
        self._flush_current_lap()
        self._session = None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _start_session(
        self,
        session_uid: str,
        track: TrackName,
        session_type: SessionType,
        assist_config: AssistConfig,
    ) -> None:
        self._session = Session(
            session_uid=session_uid,
            track=track,
            session_type=session_type,
            created_at=datetime.now(),
            steering_assist=assist_config.steering_assist,
            braking_assist=assist_config.braking_assist,
            gearbox_assist=assist_config.gearbox_assist,
            ers_assist=assist_config.ers_assist,
            drs_assist=assist_config.drs_assist,
            dynamic_racing_line=assist_config.dynamic_racing_line,
            corner_cutting_stringency=assist_config.corner_cutting_stringency,
        )
        self._session_repo.save(self._session)
        self._current_lap_number = 0
        self._telemetry_buffer = []
        self._status_buffer = []
        self._last_setup_fields = None

    def _finalise_lap(self, lap_time_ms: int, tyre_compound: int, force_invalid: bool = False) -> None:
        """Write Parquet files and persist the completed lap."""
        if self._session is None or not self._telemetry_buffer:
            return

        s1, s2, _ = self._last_sector_times
        lap_time_s = lap_time_ms / 1000.0
        s3 = max(0.0, lap_time_s - s1 - s2)

        telemetry_path = write_telemetry(
            self._session.session_uid,
            self._current_lap_number,
            self._telemetry_buffer,
        )
        status_path = ""
        if self._status_buffer:
            status_path = write_car_status(
                self._session.session_uid,
                self._current_lap_number,
                self._status_buffer,
            )
        position_path = ""
        if self._current_lap_positions:
            position_path = write_positions(
                self._session.session_uid,
                self._current_lap_number,
                self._current_lap_positions,
            )

        lap = Lap(
            lap_number=self._current_lap_number,
            lap_time=lap_time_s,
            sector_1_time=s1,
            sector_2_time=s2,
            sector_3_time=s3,
            is_valid=not self._current_lap_invalid and not force_invalid,
            tyre_compound=tyre_compound,
            weather=self._latest_conditions.weather,
            safety_car_active=self._current_lap_safety_car,
            track_temperature=self._latest_conditions.track_temperature,
            air_temperature=self._latest_conditions.air_temperature,
            telemetry_file=telemetry_path,
            status_file=status_path,
            position_file=position_path,
            session_id=self._session.id,
        )
        self._lap_repo.save(lap)
        self._session.add_lap(lap)

        logger.info(
            "Lap %d finalised: time=%.3fs valid=%s",
            self._current_lap_number,
            lap_time_s,
            lap.is_valid,
        )

        self._telemetry_buffer = []
        self._current_lap_positions = []
        self._status_buffer = []

    def _flush_current_lap(self) -> None:
        """Save an in-progress lap when the session ends unexpectedly.

        force_invalid=True: bu tur session bitirilirken yarım kaldığı için
        tamamlanmış bir tur değil — süresi (lap_time_ms=0) anlamsızdır ve
        en-iyi-tur/referans hesaplamalarına asla girmemesi gerekir.
        """
        if self._current_lap_number > 0 and self._telemetry_buffer:
            logger.info(
                "Flushing in-progress lap %d on session end (marked invalid).",
                self._current_lap_number,
            )
            self._finalise_lap(0, 0, force_invalid=True)
