"""Canlı Session ekranı — UI dokümanı §2.3, LiveSessionScreen.tsx görsel diline uyarlandı.

Kasıtlı olarak sade: kullanıcı zaten oyunu oynuyor, bu ekrana bakma ihtiyacı
neredeyse yok. Yalnızca "sistem çalışıyor" güvencesi verir. Gerçek analiz
Lap Analizi ekranında, session sonrasında yapılır.

start_monitoring() yalnızca "Başla" butonuna basıldığında MainWindow
tarafından çağrılır — sayfa oluşturulduğunda otomatik başlamaz.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.f125_udp.telemetry_receiver import TelemetryReceiver
from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager

logger = get_logger(__name__)

_TICK_INTERVAL_MS = 1000
_STALE_THRESHOLD_SECONDS = 5.0

class CanliSessionPage(QWidget):
    """Session sırasında gösterilen minimal durum ekranı.

    Signals:
        session_ended: Kullanıcı "Session'ı Bitir"e bastı. MainWindow bunu
                       dinleyip sidebar/panel navigasyonunun kilidini açar.
    """

    session_ended = pyqtSignal()

    def __init__(
        self, telemetry_receiver: TelemetryReceiver, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._receiver = telemetry_receiver
        self._last_lap_count = -1
        self._stale_warning_shown = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        # --- Üst satır: durum pili + anlık istatistik çipleri ---
        top_row = QHBoxLayout()

        self._status_pill = QFrame()
        pill_layout = QHBoxLayout(self._status_pill)
        pill_layout.setContentsMargins(12, 5, 12, 5)
        self._status_dot = QLabel("●")
        pill_layout.addWidget(self._status_dot)
        self._status_text = QLabel("Session bekleniyor")
        self._status_text.setStyleSheet("font-size: 12px; font-weight: 500; background: transparent;")
        pill_layout.addWidget(self._status_text)
        top_row.addWidget(self._status_pill)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        # --- Temel Session Bilgisi ---
        self._session_info_label = QLabel("Session bekleniyor...")
        self._session_info_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(self._session_info_label)

        # --- Tamamlanan Tur Listesi ---
        self._lap_list = QListWidget()
        layout.addWidget(self._lap_list)
        
        # --- Session'ı Bitir ---
        self._end_button = QPushButton("Bitir")
        self._end_button.setEnabled(False)
        self._end_button.setFixedHeight(40)
        self._end_button.setStyleSheet(
            f"QPushButton {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.1)};"
            f"  border: 1px solid {theme_module.rgba(theme_module.ACCENT_RED, 0.25)}; border-radius: 10px;"
            f"  color: {theme_module.ACCENT_RED}; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.16)}; }}"
            f"QPushButton:disabled {{ color: {theme_module.TEXT_MUTED}; background-color: transparent;"
            f"  border-color: {theme_module.BORDER}; }}"
        )
        self._end_button.clicked.connect(self._on_end_session)
        layout.addWidget(self._end_button)

        self._timer = QTimer(self)
        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)
        self._timer.timeout.connect(self._tick)

    def _on_theme_changed(self) -> None:
        """Aktif duruma göre doğru pil rengini yeniden uygular."""
        if not self._end_button.isEnabled():
            self._set_status_waiting()
        elif self._stale_warning_shown:
            self._set_status_disconnected()
        else:
            self._set_status_recording()
        self._update_dynamic_styles()

    def _update_dynamic_styles(self) -> None:
        """Tema değiştiğinde çip ve butonların stillerini güncel modülden tekrar okuyarak uygular."""

        # Bitir butonunun temasını da yeni renklere göre güncelle
        self._end_button.setStyleSheet(
            f"QPushButton {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.1)};"
            f"  border: 1px solid {theme_module.rgba(theme_module.ACCENT_RED, 0.25)}; border-radius: 10px;"
            f"  color: {theme_module.ACCENT_RED}; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.16)}; }}"
            f"QPushButton:disabled {{ color: {theme_module.TEXT_MUTED}; background-color: transparent;"
            f"  border-color: {theme_module.BORDER}; }}"
        )

    def start_monitoring(self) -> None:
        """MainWindow tarafından "Başla" sonrası çağrılır."""
        self._last_lap_count = -1
        self._stale_warning_shown = False
        self._lap_list.clear()
        self._session_info_label.setText("Session bekleniyor...")
        self._set_status_recording()
        self._end_button.setEnabled(True)
        self._timer.start(_TICK_INTERVAL_MS)

    def _tick(self) -> None:
        session = self._receiver.session_manager.current_session
        if session is not None and session.lap_count != self._last_lap_count:
            self._session_info_label.setText(
                f"{session.track.display_name} — {session.session_type.display_name} "
                f"— {session.lap_count} tur tamamlandı"
            )
            self._refresh_lap_list(session)
            self._last_lap_count = session.lap_count
            self._stale_warning_shown = False        

        idle_seconds = self._receiver.seconds_since_last_packet()
        if idle_seconds is not None and idle_seconds > _STALE_THRESHOLD_SECONDS:
            if not self._stale_warning_shown:
                self._set_status_disconnected()
                self._stale_warning_shown = True
        elif self._stale_warning_shown:
            self._set_status_recording()
            self._stale_warning_shown = False

    def _refresh_lap_list(self, session) -> None:  # type: ignore[no-untyped-def]
        self._lap_list.clear()
        for lap in session.laps:
            minutes, seconds = divmod(lap.lap_time, 60)
            time_text = f"{int(minutes)}:{seconds:06.3f}"
            validity = "Geçerli" if lap.is_valid else "Geçersiz"
            item = QListWidgetItem(f"Tur {lap.lap_number} — {time_text} ({validity})")
            if not lap.is_valid:
                item.setForeground(Qt.GlobalColor.gray)
            self._lap_list.addItem(item)

    def _set_status_waiting(self) -> None:
        self._status_pill.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.rgba(theme_module.TEXT_SECONDARY, 0.06)};"
            f"  border: 1px solid {theme_module.BORDER}; border-radius: 100px; }}"
        )
        self._status_dot.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 10px; background: transparent;")
        self._status_text.setText("Session bekleniyor")
        self._status_text.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; font-weight: 500; background: transparent;")

    def _set_status_recording(self) -> None:
        self._status_pill.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.rgba(theme_module.GREEN, 0.08)};"
            f"  border: 1px solid {theme_module.rgba(theme_module.GREEN, 0.2)}; border-radius: 100px; }}"
        )
        self._status_dot.setStyleSheet(f"color: {theme_module.GREEN}; font-size: 10px; background: transparent;")
        self._status_text.setText("Telemetri kaydediliyor")
        self._status_text.setStyleSheet(f"color: {theme_module.GREEN}; font-size: 12px; font-weight: 500; background: transparent;")

    def _set_status_disconnected(self) -> None:
        self._status_pill.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.08)};"
            f"  border: 1px solid {theme_module.rgba(theme_module.ACCENT_RED, 0.2)}; border-radius: 100px; }}"
        )
        self._status_dot.setStyleSheet(f"color: {theme_module.ACCENT_RED}; font-size: 10px; background: transparent;")
        self._status_text.setText("Telemetri alınamıyor")
        self._status_text.setStyleSheet(f"color: {theme_module.ACCENT_RED}; font-size: 12px; font-weight: 500; background: transparent;")
        logger.warning("Canlı Session ekranı: telemetri akışı durdu.")

    def _on_end_session(self) -> None:
        self._timer.stop()
        self._receiver.stop()
        self._session_info_label.setText(
            self._session_info_label.text() + "  [Session sonlandırıldı]"
        )
        self._set_status_waiting()
        self._end_button.setEnabled(False)
        logger.info("Session bitirildi")
        self.session_ended.emit()