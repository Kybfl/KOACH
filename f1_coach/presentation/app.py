"""KOACH GUI giriş noktası.

CLI telemetri test aracından (f1_coach/__main__.py) ayrı tutulur — bu
dosya QApplication'ı başlatıp MainWindow'u gösterir.

Tema, MainWindow (ve dolayısıyla tüm sayfa modülleri) import edilmeden
ÖNCE belirlenir — bkz. theme.py'deki set_active_theme() docstring'i.
ThemeManager, sonrasındaki her runtime değişikliğini yönetir.
"""

import sys

from PyQt6.QtWidgets import QApplication

from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.orm.database import init_db

logger = get_logger(__name__)


def run() -> None:
    """KOACH masaüstü uygulamasını başlatır."""
    init_db()
    logger.info("KOACH GUI starting...")

    # --- Tema/ölçek belirleme: MainWindow import edilmeden önce yapılmalı ---
    from f1_coach.infrastructure.storage.repositories.sqlite_profile_repository import (
        SQLiteProfileRepository,
    )
    from f1_coach.presentation.theme import set_active_theme
    from f1_coach.presentation.theme_manager import ThemeManager

    bootstrap_profile_repo = SQLiteProfileRepository()
    bootstrap_profile = bootstrap_profile_repo.get_current()
    set_active_theme(bootstrap_profile.theme if bootstrap_profile else "dark")

    theme_manager = ThemeManager.instance()
    if bootstrap_profile is not None:
        theme_manager.set_scale(bootstrap_profile.ui_scale)

    # --- Artık MainWindow (ve tüm sayfa modülleri) güvenle import edilebilir ---
    from f1_coach.infrastructure.storage.repositories.sqlite_lap_repository import (
        SQLiteLapRepository,
    )
    from f1_coach.infrastructure.storage.repositories.sqlite_session_repository import (
        SQLiteSessionRepository,
    )
    from f1_coach.infrastructure.udp.telemetry_receiver import TelemetryReceiver
    from f1_coach.presentation.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyleSheet(theme_manager.build_stylesheet())
    theme_manager.theme_changed.connect(lambda: app.setStyleSheet(theme_manager.build_stylesheet()))

    profile_repo = bootstrap_profile_repo
    session_repo = SQLiteSessionRepository()
    lap_repo = SQLiteLapRepository()
    telemetry_receiver = TelemetryReceiver(session_repo, lap_repo)

    window = MainWindow(profile_repo, session_repo, lap_repo, telemetry_receiver)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()