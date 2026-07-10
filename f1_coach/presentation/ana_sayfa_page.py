"""Ana Sayfa — UI dokümanı §2.1, HomeScreen.tsx görsel diline uyarlandı.

Onboarding turu şimdilik kapsam dışı bırakıldı (kullanıcı isteği). Sayfa:
  - Karşılama başlığı + alt metin
  - Hızlı istatistik şeridi (gerçek DB verisinden hesaplanır)
  - AI yapılandırma uyarı banner'ı (eksikse)
  - Özellik kartları
  - Son session'lar listesi (gerçek veriden, en fazla 5 kayıt)
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager
from f1_coach.domain.ports.profile_repository import ProfileRepository
from f1_coach.domain.ports.session_repository import SessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.security.credential_store import has_api_key
from f1_coach.presentation.banner_widget import WarningBanner


logger = get_logger(__name__)

_FEATURES = [
    ("📶",  theme_module.GREEN, "UDP Telemetrisi",
     "F1 25 oyunundan gerçek zamanlı telemetri verisini UDP üzerinden yakala ve kaydet."),
    ("🛡",  theme_module.PURPLE, "Oyuna Müdahale Yok",
     "Tamamen pasif dinleme — oyun verilerine yalnızca okuma erişimi, hiçbir mod veya enjeksiyon yok."),
    ("🧠",  theme_module.ORANGE, "Session Sonrası AI Analiz",
     "Sürüşünü yüklediğin AI modeline analiz ettir, kişiselleştirilmiş geri bildirim al."),
]

_MAX_RECENT_SESSIONS = 5


def _format_lap_time(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}:{secs:06.3f}"


def _make_feature_card(icon: str, color: str, title: str, description: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
        "  border-radius: 14px; padding: 16px; }"
    )
    layout = QVBoxLayout(card)

    icon_box = QLabel(icon)
    icon_box.setFixedSize(38, 38)
    icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setStyleSheet(
        f"background-color: { theme_module.rgba(color, 0.14)}; border-radius: 10px; font-size: 17px;"
    )
    layout.addWidget(icon_box)

    title_label = QLabel(title)
    title_label.setWordWrap(True)
    title_label.setStyleSheet("font-weight: 600; font-size: 14px; background: transparent;")
    layout.addWidget(title_label)

    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    desc_label.setStyleSheet(f"color: { theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
    layout.addWidget(desc_label)

    return card

class _SessionRow(QFrame):
    """Tıklanabilir son session satırı — Lap Analizi'ne yönlendirir.

    Signals:
        clicked: satıra tıklandı, session_id taşır.
    """

    clicked = pyqtSignal(int)

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

    def __init__(
        self,
        profile_repo: ProfileRepository,
        session_repo: SessionRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._profile_repo = profile_repo
        self._session_repo = session_repo

        self._layout = QVBoxLayout(self)
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

        # --- Özellik kartları ---
        features_header = QLabel("ÖZELLİKLER")
        features_header.setStyleSheet(
            f"color: { theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
        )
        self._layout.addWidget(features_header)

        self._features_row = QHBoxLayout()
        self._features_row.setSpacing(14)
        self._layout.addLayout(self._features_row)
        self._rebuild_feature_cards()

        ThemeManager.instance().theme_changed.connect(self._rebuild_feature_cards)

        # --- Son session'lar ---
        sessions_header = QLabel("SON SESSIONLAR")
        sessions_header.setStyleSheet(
            f"color: { theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
        )
        self._layout.addWidget(sessions_header)

        self._sessions_container = QVBoxLayout()
        self._sessions_container.setSpacing(8)
        self._layout.addLayout(self._sessions_container)

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
        self._update_recent_sessions()

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

    def _update_recent_sessions(self) -> None:
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
