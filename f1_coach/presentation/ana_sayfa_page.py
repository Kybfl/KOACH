"""Ana Sayfa — UI dokümanı §2.1, HomeScreen.tsx görsel diline uyarlandı.

Onboarding turu şimdilik kapsam dışı bırakıldı (kullanıcı isteği). Sayfa:
  - Karşılama başlığı + alt metin
  - Hızlı istatistik şeridi (gerçek DB verisinden hesaplanır)
  - AI yapılandırma uyarı banner'ı (eksikse)
  - Özellik kartları
  - Son session'lar listesi (gerçek veriden, en fazla 5 kayıt)
"""

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon 
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager
from f1_coach.presentation.confirm_dialog import confirm

from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.domain.ports.profile_repository import ProfileRepository
from f1_coach.domain.ports.f125.session_repository import SessionRepository

from f1_coach.infrastructure.storage.fsae.parquet_writer import delete_session_files
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.security.credential_store import has_api_key

from f1_coach.presentation.banner_widget import WarningBanner


logger = get_logger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent
ICONS_DIR = CURRENT_DIR / "assets" / "icons"

_FEATURES = [
    ("udp.svg",  theme_module.GREEN, "UDP Telemetrisi",
     "F1 25 oyunundan gerçek zamanlı telemetri verisini UDP üzerinden yakala ve kaydet."),
    ("no-disturb.svg",  theme_module.PURPLE, "Oyuna Müdahale Yok",
     "Tamamen pasif dinleme — oyun verilerine yalnızca okuma erişimi, hiçbir mod veya enjeksiyon yok."),
    ("ai.svg",  theme_module.ORANGE, "Session Sonrası AI Analiz",
     "Sürüşünü yüklediğin AI modeline analiz ettir, kişiselleştirilmiş geri bildirim al."),
]

_MAX_RECENT_SESSIONS = 5


def _format_lap_time(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}:{secs:06.3f}"


def _make_feature_card(icon_filename: str, color: str, title: str, description: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
        "  border-radius: 14px; padding: 16px; }"
    )
    layout = QVBoxLayout(card)

    icon_box = QLabel()
    # Kutunun boyutu
    icon_box.setFixedSize(48, 48)
    icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setStyleSheet(
        f"background-color: {theme_module.rgba(color, 0.14)}; border-radius: 12px;"
    )
    
    icon_path = ICONS_DIR / icon_filename
    if icon_path.exists():
        pixmap = QPixmap(str(icon_path))
        scaled_pixmap = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        icon_box.setPixmap(scaled_pixmap)
    else:
        logger.warning(f"Ikon bulunamadi: {icon_path}")
        icon_box.setText("?")
        icon_box.setStyleSheet(icon_box.styleSheet() + " font-size: 20px; font-weight: bold;")

    layout.addWidget(icon_box, alignment=Qt.AlignmentFlag.AlignHCenter)

    title_label = QLabel(title)
    title_label.setWordWrap(True)
    title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    title_label.setStyleSheet("font-weight: 600; font-size: 14px; background: transparent;")
    layout.addWidget(title_label)

    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    # Açıklamayı da ortaya hizalıyoruz (Gözüne hoş gelmezse bu satırı silebilirsin)
    desc_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    desc_label.setStyleSheet(f"color: { theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
    layout.addWidget(desc_label)

    return card

class _SessionRow(QFrame):
    """Tıklanabilir son session satırı — Lap Analizi'ne yönlendirir.

    Signals:
        clicked: satıra tıklandı, session_id taşır.
    """

    clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, session_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_id = session_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.clicked.emit(self._session_id)
        super().mousePressEvent(event)

def _make_session_row(session) -> QFrame:  # type: ignore[no-untyped-def]
    row = _SessionRow(session.id)
    row.setStyleSheet(
        f"QFrame {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
        "  border-radius: 10px; }"
        f"QFrame:hover {{ border: 1px solid #9B30FF; }}"
    )
    layout = QHBoxLayout(row)
    layout.setContentsMargins(14, 10, 14, 10)

    dot = QLabel("●")
    dot.setStyleSheet(f"color: {theme_module.GREEN}; font-size: 8px; background: transparent; border: none;")
    layout.addWidget(dot)

    track_label = QLabel(session.track.display_name)
    track_label.setStyleSheet("font-weight: 600; font-size: 13px; background: transparent; border: none;")
    layout.addWidget(track_label, stretch=1)

    best_lap = session.best_lap
    best_text = _format_lap_time(best_lap.lap_time) if best_lap else "—"
    best_label = QLabel(best_text)
    best_label.setStyleSheet(f"color: { theme_module.GREEN}; font-size: 13px; font-weight: 600; background: transparent; border: none;")
    layout.addWidget(best_label)

    laps_label = QLabel(f"{session.lap_count} tur")
    laps_label.setStyleSheet(f"color: { theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent; border: none;")
    layout.addWidget(laps_label)

    weather = session.dominant_weather
    weather_text = weather.display_name if weather else "—"
    weather_label = QLabel(weather_text)
    weather_label.setStyleSheet(f"color: { theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent; border: none;")
    layout.addWidget(weather_label)

    date_label = QLabel(session.created_at.strftime("%d.%m.%Y"))
    date_label.setStyleSheet(f"color: { theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent; border: none;")
    layout.addWidget(date_label)

    return row

def _make_fsae_session_row(session) -> QFrame:  # type: ignore[no-untyped-def]
    row = _SessionRow(session.id)
    status_color = theme_module.GREEN if session.is_labeled else theme_module.YELLOW
    row.setStyleSheet(
        f"QFrame {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
        "  border-radius: 10px; }"
        f"QFrame:hover {{ border: 1px solid #9B30FF; }}"
    )
    layout = QHBoxLayout(row)
    layout.setContentsMargins(14, 10, 14, 10)

    dot = QLabel("●")
    dot.setStyleSheet(f"color: {status_color}; font-size: 8px; background: transparent; border: none;")
    layout.addWidget(dot)

    name_label = QLabel(session.name)
    name_label.setStyleSheet("font-weight: 600; font-size: 13px; background: transparent; border: none;")
    layout.addWidget(name_label, stretch=1)

    status_text = "Etiketlendi" if session.is_labeled else "Etiketleme bekliyor"
    status_label = QLabel(status_text)
    status_label.setStyleSheet(
        f"color: {status_color}; font-size: 12px; font-weight: 600; background: transparent; border: none;"
    )
    layout.addWidget(status_label)

    date_label = QLabel(session.imported_at.strftime("%d.%m.%Y"))
    date_label.setStyleSheet(f"color: { theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent; border: none;")
    layout.addWidget(date_label)

    delete_button = QPushButton() 
    icon_path = ICONS_DIR / "trash.svg"
    delete_button.setIcon(QIcon(str(icon_path)))
    delete_button.setIconSize(QSize(14, 14)) 
    delete_button.setObjectName("PrimaryButton")
    delete_button.setFixedSize(27, 27)
    delete_button.setToolTip("Session'ı sil")
    delete_button.clicked.connect(lambda: row.delete_clicked.emit(session.id))
    layout.addWidget(delete_button)

    return row


class AnaSayfaPage(QWidget):
    """Uygulama açılışında karşılayan hub ekranı.

    Signals:
        settings_requested: AI yapılandırma banner'ındaki butona basıldı.
        session_selected: Son session satırlarından birine tıklandı,
                          session_id taşır. MainWindow bunu Lap Analizi'ne
                          yönlendirmek için dinler.
    """

    settings_requested = pyqtSignal()
    session_selected = pyqtSignal(int)
    fsae_session_selected = pyqtSignal(int)   

    def __init__(
        self,
        profile_repo: ProfileRepository,
        session_repo: SessionRepository,
        vehicle_session_repo: VehicleSessionRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._profile_repo = profile_repo
        self._session_repo = session_repo
        self._vehicle_session_repo = vehicle_session_repo

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        outer_layout.addWidget(scroll_area)

        content = QWidget()
        scroll_area.setWidget(content)

        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(32, 32, 32, 32)
        self._layout.setSpacing(22)

        # --- Karşılama başlığı ---
        eyebrow = QLabel("⚡ KOACH · F1 25")
        eyebrow.setStyleSheet("color: #E10600; font-size: 11px; font-weight: 600;")
        self._layout.addWidget(eyebrow)

        self._greeting_label = QLabel()
        self._greeting_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        self._layout.addWidget(self._greeting_label)

        subtitle = QLabel("Sürüşünü analiz et, her turda daha iyi ol.")
        subtitle.setStyleSheet(f"color: { theme_module.TEXT_SECONDARY}; font-size: 13px;")
        self._layout.addWidget(subtitle)

        # --- AI yapılandırma banner'ı ---
        self._ai_banner = WarningBanner(
            "AI koçluk analizi için henüz bir sağlayıcı yapılandırılmadı.",
            "Ayarlar'a Git",
        )
        self._ai_banner.action_clicked.connect(self.settings_requested.emit)
        self._layout.addWidget(self._ai_banner)

        self._features_row = QHBoxLayout()
        self._features_row.setSpacing(14)
        self._layout.addLayout(self._features_row)
        self._rebuild_feature_cards()

        ThemeManager.instance().theme_changed.connect(self._rebuild_feature_cards)

        # --- Son session'lar ---
        self.f125_sessions_header = QLabel("SON F1 25 SESSION'LARI")
        self.f125_sessions_header.setStyleSheet(
            f"color: { theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
        )
        self._layout.addWidget(self.f125_sessions_header)

        self._sessions_container = QVBoxLayout()
        self._sessions_container.setSpacing(8)
        self._layout.addLayout(self._sessions_container)

        self._fsae_sessions_header = QLabel("SON FSAE SESSION'LARI")
        self._fsae_sessions_header.setStyleSheet(
            f"color: { theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
        )
        self._layout.addWidget(self._fsae_sessions_header)

        self._fsae_sessions_container = QVBoxLayout()
        self._fsae_sessions_container.setSpacing(8)
        self._layout.addLayout(self._fsae_sessions_container)

        self._layout.addStretch(1)
        ThemeManager.instance().theme_changed.connect(self.refresh)
        self.refresh()

    def _rebuild_feature_cards(self) -> None:
        """Kartları temadan bağımsız yeniden inşa eder — renk import anında
        değil, bu metod her çağrıldığında theme modülünden okunur."""
        while self._features_row.count():
            item = self._features_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for icon, color, title, desc in _FEATURES:
            self._features_row.addWidget(_make_feature_card(icon, color, title, desc))

    def refresh(self) -> None:
        """Sidebar'dan Ana Sayfa'ya her dönüşte çağrılır — güncel veriyi çeker."""
        self._update_greeting()
        self._update_ai_banner()
        self._update_recent_f125_sessions()
        self._update_recent_fsae_sessions()

    def _update_greeting(self) -> None:
        profile = self._profile_repo.get_current()
        name = profile.name if profile else "Sürücü"
        self._greeting_label.setText(f"Hoş geldin, {name} 👋")


    def _update_ai_banner(self) -> None:
        profile = self._profile_repo.get_current()
        configured = bool(
            profile and profile.is_ai_configured and has_api_key(profile.ai_provider)
        )
        self._ai_banner.setVisible(not configured)

    def _update_recent_f125_sessions(self) -> None:
        sessions = self._vehicle_session_repo.get_all()
        self._fsae_sessions_header.setText(f"SON F1 25 SESSION'LARI ({len(sessions)})")

        while self._sessions_container.count():
            item = self._sessions_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sessions = self._session_repo.get_all()
        if not sessions:
            empty = QFrame()
            empty.setFrameShape(QFrame.Shape.NoFrame)
            empty.setStyleSheet(
                f"QFrame {{ border: 1px dashed { theme_module.BORDER}; border-radius: 14px; }}"
            )
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(24, 32, 24, 32)
            title = QLabel("Henüz session yok")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("font-size: 14px; font-weight: 500; background: transparent;")
            empty_layout.addWidget(title)
            desc = QLabel(
                "Bir F1 25 sessionı başlatıp Canlı Session sekmesine geç. "
                "Veriler otomatik kaydedilecek."
            )
            desc.setWordWrap(True)
            desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc.setStyleSheet(f"color: { theme_module.TEXT_MUTED}; font-size: 12px; background: transparent;")
            empty_layout.addWidget(desc)
            self._sessions_container.addWidget(empty)
            return

        for session in sessions[:_MAX_RECENT_SESSIONS]:
            row = _make_session_row(session)
            row.clicked.connect(self.session_selected.emit)
            self._sessions_container.addWidget(row)

        logger.debug("Son session listesi guncellendi: %d kayit gosteriliyor.", min(len(sessions), _MAX_RECENT_SESSIONS))

    def _update_recent_fsae_sessions(self) -> None:
        sessions = self._vehicle_session_repo.get_all()
        self._fsae_sessions_header.setText(f"SON FSAE SESSION'LARI ({len(sessions)})")

        while self._fsae_sessions_container.count():
            item = self._fsae_sessions_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not sessions:
            empty = QFrame()
            empty.setFrameShape(QFrame.Shape.NoFrame)
            empty.setStyleSheet(
                f"QFrame {{ border: 1px dashed { theme_module.BORDER}; border-radius: 14px; }}"
            )
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(24, 32, 24, 32)
            title = QLabel("Henüz FSAE session'ı yok")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("font-size: 14px; font-weight: 500; background: transparent;")
            empty_layout.addWidget(title)
            desc = QLabel(
                "Bir CAN log dosyasını içe aktarıp etiketledikten sonra "
                "session'lar burada listelenecek."
            )
            desc.setWordWrap(True)
            desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc.setStyleSheet(f"color: { theme_module.TEXT_MUTED}; font-size: 12px; background: transparent;")
            empty_layout.addWidget(desc)
            self._fsae_sessions_container.addWidget(empty)
            return

        for session in sessions[:_MAX_RECENT_SESSIONS]:
            row = _make_fsae_session_row(session)
            row.clicked.connect(self.fsae_session_selected.emit)
            row.delete_clicked.connect(self._on_fsae_delete_clicked)   
            self._fsae_sessions_container.addWidget(row)
    

    def _on_fsae_delete_clicked(self, session_id: int) -> None:
        """FSAE session satırındaki çöp kutusu ikonuna basıldığında çağrılır.

        Onay alındıktan sonra hem SQLite kaydını (VehicleSessionRepository.delete
        — CASCADE ile ChannelMapping'leri de siler) hem de diskteki Parquet
        dosyalarını (raw_can_frames + decoded_telemetry) kaldırır. Repository
        silme işi filesystem'i bilmiyor — session_gecmisi_page.py'deki F125
        silme akışıyla aynı sorumluluk ayrımı.
        """
        if not confirm(
        self, "Emin misin?",
        "Bu FSAE session'ı ve tüm etiketleme/telemetri verileri kalıcı olarak "
        "silinecek. Devam edilsin mi?",
        ):
            return

        session = self._vehicle_session_repo.get_by_id(session_id)
        if session is None:
            return

        session_identifier = Path(session.raw_can_file).parent.name if session.raw_can_file else ""

        self._vehicle_session_repo.delete(session_id)
        if session_identifier:
            delete_session_files(session_identifier)

        logger.info("FSAE session silindi: id=%d name=%s", session_id, session.name)
        self._update_recent_fsae_sessions()