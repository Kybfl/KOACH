"""TelemetryReceiver — UDP capture loop.

Binds to UDP port 20777 and runs a blocking receive loop in a background
thread. Each datagram is parsed, mapped to domain objects, and forwarded
to SessionManager.

Thread model:
    Main thread  → starts/stops TelemetryReceiver
    Capture thread → recv loop (blocking socket, exits when _running = False)

The socket has a 1-second timeout so the loop can check _running without
blocking forever when the game is not sending data.
"""

import socket
import threading
import time

from f1_coach.domain.ports.f125.car_setup_repository import CarSetupRepository
from f1_coach.domain.ports.f125.lap_repository import LapRepository
from f1_coach.domain.ports.f125.session_repository import SessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.f125_udp.parsers.packet_parsers import (
    parse_car_setup,
    parse_car_status,
    parse_car_telemetry,
    parse_header,
    parse_lap_data,
    parse_motion,
    parse_session,
)
from f1_coach.infrastructure.f125_udp.session_manager import SessionManager
from f1_coach.infrastructure.f125_udp.telemetry_mapper import (
    map_assist_config,
    map_car_position,
    map_car_setup_fields,
    map_car_status_point,
    map_lap_distance,
    map_lap_validity,
    map_sector_times,
    map_session_conditions,
    map_session_info,
    map_telemetry_point,
)

logger = get_logger(__name__)

_UDP_IP = "0.0.0.0"
_UDP_PORT = 20777
_BUFFER_SIZE = 2048
_SOCKET_TIMEOUT = 1.0  # seconds — allows the loop to check _running


class TelemetryReceiver:
    """Receives F1 25 UDP telemetry and forwards parsed data to SessionManager."""

    def __init__(
        self,
        session_repo: SessionRepository,
        lap_repo: LapRepository,
        car_setup_repo: CarSetupRepository
    ) -> None:
        self._manager = SessionManager(session_repo, lap_repo, car_setup_repo)
        self._running = False
        self._thread: threading.Thread | None = None

        # Latest track position from the most recent Lap Data packet.
        # Shared between packet handlers within the same thread — no lock needed.
        self._track_position: float = 0.0
        self._track_length: float = 0.0
        self._player_index: int = 0
        self._tyre_compound: int = 16   # default: C1
        self._last_packet_time: float | None = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def session_manager(self) -> SessionManager:
        return self._manager

    def seconds_since_last_packet(self) -> float | None:
        """Return seconds since the last UDP datagram was received.

        Returns None if no packet has ever been received in this run.
        Used by the caller to detect a stalled/disconnected telemetry feed
        (e.g. game closed or UDP toggled off) without guessing based on
        stale in-memory state.
        """
        if self._last_packet_time is None:
            return None
        return time.monotonic() - self._last_packet_time

    def start(self) -> None:
        """Start the UDP capture thread."""
        if self._running:
            logger.warning("TelemetryReceiver already running.")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="TelemetryCapture",
            daemon=True,
        )
        self._thread.start()
        logger.info("TelemetryReceiver started on port %d.", _UDP_PORT)

    def stop(self) -> None:
        """Signal the capture thread to stop and wait for it to exit."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._manager.end_session()
        logger.info("TelemetryReceiver stopped.")

    # ------------------------------------------------------------------
    # Capture loop (runs in background thread)
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(_SOCKET_TIMEOUT)

        try:
            sock.bind((_UDP_IP, _UDP_PORT))
            logger.info("UDP socket bound to %s:%d", _UDP_IP, _UDP_PORT)

            while self._running:
                try:
                    data, _ = sock.recvfrom(_BUFFER_SIZE)
                except TimeoutError:
                    continue  # no data yet — check _running and loop

                self._dispatch(data)

        except OSError as exc:
            logger.error("UDP socket error: %s", exc)
        finally:
            sock.close()

    def _dispatch(self, data: bytes) -> None:
        """Route a raw UDP datagram to the appropriate handler."""
        header = parse_header(data)
        if header is None:
            return

        self._last_packet_time = time.monotonic()
        self._player_index = header.m_playerCarIndex
        packet_id = header.m_packetId

        if packet_id == 0:
            self._handle_motion(data)
        elif packet_id == 1:
            self._handle_session(data)
        elif packet_id == 2:
            self._handle_lap(data, header)
        elif packet_id == 5:                      # ← yeni
            self._handle_car_setup(data)
        elif packet_id == 6:
            self._handle_telemetry(data, header)
        elif packet_id == 7:
            self._handle_car_status(data, header)
        # All other packet IDs are silently ignored

    # ------------------------------------------------------------------
    # Per-packet handlers
    # ------------------------------------------------------------------

    def _handle_motion(self, data: bytes) -> None:
        packet = parse_motion(data)
        if packet is None:
            return
        car = packet.m_carMotionData[self._player_index]
        x, z = map_car_position(car)
        self._manager.on_car_position(x, z, self._track_position)
    
    def _handle_session(self, data: bytes) -> None:
        packet = parse_session(data)
        if packet is None:
            return
        uid, track, session_type = map_session_info(packet)
        self._track_length = float(packet.m_trackLength)
        assist_config = map_assist_config(packet)
        self._manager.on_session_packet(
            uid, track, session_type, self._track_length, assist_config
        )
        self._manager.on_session_conditions(map_session_conditions(packet))

    def _handle_lap(self, data: bytes, header) -> None:
        packet = parse_lap_data(data)
        if packet is None:
            return
        car = packet.m_lapData[self._player_index]
        self._track_position = map_lap_distance(car, self._track_length)
        self._tyre_compound = 16  # updated by car status; use last known value here
        sector_times = map_sector_times(car)
        is_valid = map_lap_validity(car)
        self._manager.on_lap_packet(
            lap_number=int(car.m_currentLapNum),
            lap_time_ms=int(car.m_lastLapTimeInMS),
            sector_times=sector_times,
            is_valid=is_valid,
            tyre_compound=self._tyre_compound,
        )

    def _handle_telemetry(self, data: bytes, header) -> None:
        packet = parse_car_telemetry(data)
        if packet is None:
            return
        car = packet.m_carTelemetryData[self._player_index]
        point = map_telemetry_point(header, car, self._track_position)
        self._manager.on_telemetry_point(point)

    def _handle_car_status(self, data: bytes, header) -> None:
        packet = parse_car_status(data)
        if packet is None:
            return
        car = packet.m_carStatusData[self._player_index]
        self._tyre_compound = int(car.m_actualTyreCompound)
        point = map_car_status_point(header, car, self._track_position)
        self._manager.on_car_status_point(point)

    def _handle_car_setup(self, data: bytes) -> None:
        packet = parse_car_setup(data)
        if packet is None:
            return
        car = packet.m_carSetupData[self._player_index]
        fields = map_car_setup_fields(car)
        self._manager.on_car_setup_packet(fields)