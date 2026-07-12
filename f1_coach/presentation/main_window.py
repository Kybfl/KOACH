"""MainWindow — navigasyon iskeletini birleştiren ana pencere.

Yapı:
    [Sidebar (Katman 1, sabit)] [SecondaryPanel (Katman 2, kayar)] [İçerik alanı]

İçerik alanı bir QStackedWidget'tır; her sayfa bu dosyada bir index'e
sahiptir. Sayfalar arası geçiş yalnızca burada, tek bir yerde yönetilir.

Başlangıç yönlendirmesi (UI dokümanı §2.6):
    Profil varsa  → doğrudan Ana Sayfa
    Profil yoksa  → Profil sayfası (onboarding)
"""
from pathlib import Path

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from PyQt6.QtGui import QIcon

from f1_coach.application.coaching_engine import CoachingEngine
from f1_coach.infrastructure.ai.adapter_factory import create_ai_adapter
from f1_coach.infrastructure.security.credential_store import get_api_key
from f1_coach.presentation.ayarlar_page import AyarlarPage

from f1_coach.presentation.f1_25_landing_page import F1_25LandingPage
from f1_coach.presentation.session_gecmisi_page import SessionGecmisiPage
from f1_coach.infrastructure.udp.telemetry_receiver import TelemetryReceiver
from f1_coach.presentation.canli_session_page import CanliSessionPage
from f1_coach.presentation.lap_analizi_page import LapAnaliziPage
from f1_coach.infrastructure.storage.repositories.sqlite_lap_repository import (
    SQLiteLapRepository,
)
from f1_coach.domain.ports.profile_repository import ProfileRepository
from f1_coach.domain.ports.session_repository import SessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.presentation.ana_sayfa_page import AnaSayfaPage

from f1_coach.presentation.profil_page import ProfilPage
from f1_coach.presentation.secondary_panel import SecondaryPanel
from f1_coach.presentation.sidebar import Sidebar

logger = get_logger(__name__)
_ASSETS_DIR = Path(__file__).parent / "assets" 
_LOGO_DIR = _ASSETS_DIR / "logos"

class MainWindow(QMainWindow):
    """KOACH ana penceresi — tüm navigasyonun birleştiği yer."""

    def __init__(
    self,
        profile_repo: ProfileRepository,
        session_repo: SessionRepository,
        lap_repo: SQLiteLapRepository,
        telemetry_receiver: TelemetryReceiver,
    ) -> None:
        super().__init__()
        self._profile_repo = profile_repo
        self._session_repo = session_repo
        self._lap_repo = lap_repo
        self._telemetry_receiver = telemetry_receiver

        self.setWindowTitle("KOACH")
        icon_path = Path(__file__).parent / "assets" / "logos" / "koach_siyah.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1280, 900)
        
        icon_path = _LOGO_DIR /"koach_siyah.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        outer_layout.addWidget(self._build_top_bar())

        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        outer_layout.addWidget(body, stretch=1)

        # --- Katman 1: Sidebar ---
        self._sidebar = Sidebar()
        self._sidebar.profile_clicked.connect(self._show_profil)
        self._sidebar.home_clicked.connect(self._show_ana_sayfa)
        self._sidebar.f1_25_clicked.connect(self._show_f1_25_landing)
        self._sidebar.settings_clicked.connect(self._show_ayarlar)
        root_layout.addWidget(self._sidebar)

        # --- Katman 2: Kayar panel (varsayılan gizli) ---
        self._secondary_panel = SecondaryPanel()
        self._secondary_panel.live_session_clicked.connect(self._show_canli_session)
        self._secondary_panel.lap_analysis_clicked.connect(self._show_lap_analizi)
        self._secondary_panel.session_history_clicked.connect(self._show_session_gecmisi)

        # --- İçerik alanı ---
        self._content_stack = QStackedWidget()
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._secondary_panel)
        right_layout.addWidget(self._content_stack, stretch=1)
        root_layout.addWidget(right_column, stretch=1)
        
        self._build_pages()
        self._route_on_startup()

    # ------------------------------------------------------------------
    # Sayfa kurulumu
    # ------------------------------------------------------------------

    def _build_top_bar(self) -> QFrame:
        """App.tsx'teki üst bar: logo + KOACH wordmark + F1 25 rozeti."""
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(48)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        title = QLabel("KOACH")
        title.setStyleSheet("font-size: 13px; font-weight: 700")
        layout.addWidget(title)

        badge = QLabel("F1 25")
        badge.setStyleSheet(
            "background-color: rgba(225,6,0,0.12);"
            "border: 1px solid rgba(225,6,0,0.2);"
            "border-radius: 4px;"
            "color: #E10600; font-size: 9px; font-weight: 700;"
            "padding: 1px 5px;"
        )
        layout.addWidget(badge)
        layout.addStretch(1)

        return bar
    
    def _build_pages(self) -> None:
        """Her sayfayı stack'e ekler ve index'ini saklar."""
        self._ana_sayfa_page = AnaSayfaPage(self._profile_repo, self._session_repo)
        self._ana_sayfa_page.settings_requested.connect(self._show_ayarlar)
        self._ana_sayfa_page.session_selected.connect(self._open_session_from_history)
        self._page_ana_sayfa = self._content_stack.addWidget(self._ana_sayfa_page)

        self._f1_25_landing_page = F1_25LandingPage()
        self._f1_25_landing_page.start_pressed.connect(self.on_f1_25_start_pressed)
        self._page_f1_25_landing = self._content_stack.addWidget(self._f1_25_landing_page)

        self._profil_page = ProfilPage(self._profile_repo, self._session_repo)
        self._profil_page.onboarding_completed.connect(self._show_ana_sayfa)
        self._profil_page.profile_saved.connect(self._refresh_profile_badge)
        self._page_profil = self._content_stack.addWidget(self._profil_page)

        self._ayarlar_page = AyarlarPage(self._profile_repo)
        self._ayarlar_page.settings_saved.connect(self._on_settings_saved)
        self._page_ayarlar = self._content_stack.addWidget(self._ayarlar_page)

        self._canli_session_page = CanliSessionPage(self._telemetry_receiver)
        self._canli_session_page.session_ended.connect(self._on_live_session_ended)
        self._page_canli_session = self._content_stack.addWidget(self._canli_session_page)
        
        self._lap_analizi_page = LapAnaliziPage(self._session_repo, self._lap_repo, coaching_engine=None)
        self._page_lap_analizi = self._content_stack.addWidget(self._lap_analizi_page)       
        
        self._session_gecmisi_page = SessionGecmisiPage(self._session_repo)
        self._session_gecmisi_page.session_selected.connect(self._open_session_from_history)
        self._page_session_gecmisi = self._content_stack.addWidget(self._session_gecmisi_page)

        self._refresh_coaching_engine()
        self._refresh_profile_badge()

    def _route_on_startup(self) -> None:
        """UI dokümanı §2.6: profil var mı yok mu kontrolü."""
        profile = self._profile_repo.get_current()
        if profile is None:
            logger.info(
                "Profil bulunamadı — ilk kullanım akışı, Profil sayfasına yönlendiriliyor."
            )
            self._show_profil()
        else:
            logger.info("Hoş geldin %s — Ana Sayfa'ya yönlendiriliyor.", profile.name)
            self._show_ana_sayfa()

    # ------------------------------------------------------------------
    # Sayfa geçişleri
    # ------------------------------------------------------------------

    def _show_ana_sayfa(self) -> None:
        self._secondary_panel.close_panel()
        self._ana_sayfa_page.refresh()
        self._content_stack.setCurrentIndex(self._page_ana_sayfa)

    def _show_f1_25_landing(self) -> None:
        """F1 25 ikonuna her tıklamada gösterilir; ikincil panel henüz açılmaz."""
        self._secondary_panel.close_panel()
        self._content_stack.setCurrentIndex(self._page_f1_25_landing)

    def _show_profil(self) -> None:
        self._secondary_panel.close_panel()
        self._profil_page.refresh()
        self._content_stack.setCurrentIndex(self._page_profil)

    def _show_ayarlar(self) -> None:
        self._secondary_panel.close_panel()
        self._ayarlar_page.refresh()
        self._content_stack.setCurrentIndex(self._page_ayarlar)

    def _show_canli_session(self) -> None:
        self._content_stack.setCurrentIndex(self._page_canli_session)

    def _show_lap_analizi(self) -> None:
        self._lap_analizi_page.refresh()
        self._content_stack.setCurrentIndex(self._page_lap_analizi)

    def _show_session_gecmisi(self) -> None:
        self._session_gecmisi_page.refresh()
        self._content_stack.setCurrentIndex(self._page_session_gecmisi)

    def on_f1_25_start_pressed(self) -> None:
        """F1 25 Landing sayfasındaki "Başla" butonu buraya bağlanır.

        UDP dinlemeyi gerçekten başlatan ilk nokta — bu andan önce hiçbir
        sistem kaynağı kullanılmaz (UI dokümanı §2.2). Session kaydı boyunca
        diğer navigasyon kilitlenir — kullanıcının yanlışlıkla başka sayfaya
        geçip kaydı takip edememesini önlemek için.
        """
        self._telemetry_receiver.start()
        self._secondary_panel.open_panel()
        self._canli_session_page.start_monitoring()
        self._sidebar.set_navigation_locked(True)
        self._secondary_panel.set_navigation_locked(True)
        self._show_canli_session()

    def _on_live_session_ended(self) -> None:
        """CanliSessionPage.session_ended sinyali geldiğinde navigasyonun kilidini açar."""
        self._sidebar.set_navigation_locked(False)
        self._secondary_panel.set_navigation_locked(False)

    def _open_session_from_history(self, session_id: int) -> None:
        """Session Geçmişi'nden bir karta tıklanınca o session'ı Lap Analizi'nde açar."""
        self._lap_analizi_page.load_session(session_id)
        self._secondary_panel.open_panel()
        self._content_stack.setCurrentIndex(self._page_lap_analizi)

    def _refresh_coaching_engine(self) -> None:
        """Profildeki AI ayarlarına göre CoachingEngine kurar; eksikse None bırakır."""
        profile = self._profile_repo.get_current()
        if profile is None or not profile.is_ai_configured:
            self._lap_analizi_page.set_coaching_engine(None)
            return

        api_key = get_api_key(profile.ai_provider)
        if not api_key:
            self._lap_analizi_page.set_coaching_engine(None)
            return

        try:
            adapter = create_ai_adapter(profile.ai_provider, api_key)
            engine = CoachingEngine(self._lap_repo, self._session_repo, adapter)
            self._lap_analizi_page.set_coaching_engine(engine)
            logger.info("CoachingEngine kuruldu: provider=%s", profile.ai_provider)
        except Exception as exc:
            logger.error("CoachingEngine kurulamadı: %s", exc)
            self._lap_analizi_page.set_coaching_engine(None)

    def _on_settings_saved(self) -> None:
        self._refresh_coaching_engine()
        self._ana_sayfa_page.refresh()

    def _refresh_profile_badge(self) -> None:
        """Sidebar'daki profil rozetini güncel isim/fotoğrafla senkronlar."""
        profile = self._profile_repo.get_current()
        if profile is not None:
            self._sidebar.update_profile_badge(profile.name, profile.photo_path)