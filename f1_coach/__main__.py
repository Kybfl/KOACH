"""KOACH — F1 25 telemetry analysis and AI coaching.

Entry point for the Faz 3 end-to-end test.
Run with:  python -m f1_coach

Starts the UDP receiver, waits for keyboard interrupt, then stops cleanly.
UI will replace this flow in Faz 5.
"""

import signal
import time

from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.orm.database import init_db
from f1_coach.infrastructure.storage.repositories.sqlite_session_repository import (
    SQLiteSessionRepository,
)
from f1_coach.infrastructure.storage.repositories.sqlite_lap_repository import (
    SQLiteLapRepository,
)
from f1_coach.infrastructure.udp.telemetry_receiver import TelemetryReceiver

logger = get_logger(__name__)


def main() -> None:
    logger.info("KOACH starting...")

    # 1. Initialise database (creates koach.db and tables if not present)
    init_db()

    # 2. Wire up repositories
    session_repo = SQLiteSessionRepository()
    lap_repo = SQLiteLapRepository()

    # 3. Start UDP capture
    receiver = TelemetryReceiver(session_repo, lap_repo)
    receiver.start()

    logger.info("Listening for F1 25 telemetry on port 20777. Press Ctrl+C to stop.")

    # 4. Keep main thread alive; stop cleanly on a single Ctrl+C or SIGTERM.
    # A module-level flag (not a local variable) is required so the signal
    # handler can flip it and the loop below can observe the change.
    shutdown_requested = False

    def _shutdown(signum, frame):  # type: ignore[no-untyped-def]
        nonlocal shutdown_requested
        logger.info("Shutdown signal received.")
        shutdown_requested = True
        receiver.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    last_logged_lap_count = -1
    stale_warning_shown = False
    STALE_THRESHOLD_SECONDS = 5.0

    while not shutdown_requested:
        time.sleep(1)
        session = receiver.session_manager.current_session

        if session is None:
            continue

        # Only log when the lap count actually changes — avoids repeating
        # the same status line every second while nothing new is happening.
        if session.lap_count != last_logged_lap_count:
            logger.info(
                "Active session: %s / %s — %d lap(s) recorded",
                session.track.display_name,
                session.session_type.display_name,
                session.lap_count,
            )
            last_logged_lap_count = session.lap_count
            stale_warning_shown = False

        # Detect a stalled telemetry feed (game closed / UDP toggled off)
        # instead of silently sitting idle with no indication to the user.
        idle_seconds = receiver.seconds_since_last_packet()
        if (
            idle_seconds is not None
            and idle_seconds > STALE_THRESHOLD_SECONDS
            and not stale_warning_shown
        ):
            logger.warning(
                "%.0f saniyedir telemetri verisi alınamıyor. "
                "Oyun kapatılmış veya UDP telemetrisi kapatılmış olabilir. "
                "Çıkmak için Ctrl+C.",
                idle_seconds,
            )
            stale_warning_shown = True

    logger.info("KOACH stopped cleanly.")


if __name__ == "__main__":
    main()
