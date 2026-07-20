"""Ayarlar ekranı — UI dokümanı §2.7, SettingsScreen.tsx görsel diline uyarlandı.

AI provider seçimi, API key girişi (güvenli saklama credential_store
üzerinden), UDP port ve tema tercihi. Kaydedilince settings_saved sinyali
yayınlanır — MainWindow bunu dinleyip CoachingEngine'i yeniden kurar.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QSlider,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager
from f1_coach.presentation.theme import (
    ACCENT_RED,
    BORDER,
    GREEN,
    PURPLE,
    SURFACE,
    TEXT_SECONDARY,
    rgba,
)

from f1_coach.domain.ports.profile_repository import ProfileRepository

from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.security.credential_store import get_api_key, save_api_key, delete_api_key



logger = get_logger(__name__)

_PROVIDERS = [
    ("groq", "Groq (önerilen)"),
    ("anthropic", "Anthropic"),
    ("gemini", "Gemini"),
]
_THEMES = [
    ("dark", "Koyu"),
    ("light", "Açık"),
    ("graphite_mint", "Grafit & Nane"),
    ("porcelain_blue", "Porselen & Mavi"),
    ("violet_dragonfruit", "Menekşe & Ejder Meyvesi"),
]
class _NoScrollComboBox(QComboBox):
    """Scroll ile yanlışlıkla değer değişmesini engeller.

    Widget klavye odağına sahip değilse (yani kullanıcı henüz tıklamadıysa)
    fare tekerleği olayını yok sayar, event'i sayfanın scroll area'sına iletir.
    """

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class _NoScrollSpinBox(QSpinBox):
    """Scroll ile yanlışlıkla değer değişmesini engeller (bkz. _NoScrollComboBox)."""

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)

def _make_section_card(dot_color: str, title: str) -> tuple[QFrame, QVBoxLayout]:
    """Renkli nokta başlıklı ayarlar kartı iskeleti döner (kart, içerik layout'u)."""
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER};"
        "  border-radius: 16px; padding: 20px; }"
    )
    outer = QVBoxLayout(card)

    header_row = QHBoxLayout()
    dot = QLabel()
    dot.setFixedSize(7, 7)
    dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 3px;")
    header_row.addWidget(dot)
    header_label = QLabel(title)
    header_label.setStyleSheet("font-size: 14px; font-weight: 600; background: transparent;")
    header_row.addWidget(header_label)
    header_row.addStretch(1)
    outer.addLayout(header_row)

    inner = QVBoxLayout()
    outer.addLayout(inner)

    return card, inner


class AyarlarPage(QWidget):
    """Ayarlar formu.

    Signals:
        settings_saved: Ayarlar kaydedildi. MainWindow bunu dinleyip
                        CoachingEngine'i güncel provider/key ile yeniden kurar.
    """

    settings_saved = pyqtSignal()

    def __init__(self, profile_repo: ProfileRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profile_repo = profile_repo
        self._api_key_visible = False

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        outer_layout.addWidget(scroll_area)

        content = QWidget()
        scroll_area.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # ================= AI Yapılandırması =================
        ai_card, ai_content = _make_section_card(ACCENT_RED, "AI Yapılandırması")
        layout.addWidget(ai_card)

        self._provider_combo = _NoScrollComboBox()
        for value, label in _PROVIDERS:
            self._provider_combo.addItem(label, value)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        ai_content.addWidget(QLabel("AI Sağlayıcı"))
        ai_content.addWidget(self._provider_combo)
        self._provider_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        ai_content.addSpacing(10)
        ai_content.addWidget(QLabel("API Anahtarı"))

        key_row = QHBoxLayout()
        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText("sk-...")
        key_row.addWidget(self._api_key_input, stretch=1)

        self._toggle_visibility_button = QPushButton("👁")
        self._toggle_visibility_button.setFixedWidth(36)
        self._toggle_visibility_button.clicked.connect(self._on_toggle_key_visibility)
        key_row.addWidget(self._toggle_visibility_button)
        ai_content.addLayout(key_row)

        security_note_row = QHBoxLayout()
        shield = QLabel("🛡")
        shield.setStyleSheet(f"color: {GREEN}; font-size: 11px; background: transparent;")
        security_note_row.addWidget(shield)
        security_note = QLabel(
            "API anahtarın şifreli olarak işletim sistemi kimlik bilgisi "
            "deposunda saklanır, hiçbir sunucuya gönderilmez."
        )
        security_note.setWordWrap(True)
        security_note.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        security_note_row.addWidget(security_note, stretch=1)
        ai_content.addLayout(security_note_row)

        # ================= Telemetri Ayarları =================
        telemetry_card, telemetry_content = _make_section_card(GREEN, "Telemetri Ayarları")
        layout.addWidget(telemetry_card)

        telemetry_content.addWidget(QLabel("UDP Port"))
        self._udp_port_input = _NoScrollSpinBox()
        self._udp_port_input.setRange(1024, 65535)
        self._udp_port_input.setValue(20777)
        telemetry_content.addWidget(self._udp_port_input)
        self._udp_port_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        port_note = QLabel("F1 25 oyunundaki UDP portu ile eşleşmeli. Varsayılan: 20777")
        port_note.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        telemetry_content.addWidget(port_note)

        # ================= Görünüm =================
        appearance_card, appearance_content = _make_section_card(PURPLE, "Görünüm")
        layout.addWidget(appearance_card)

        self._section_cards = [ai_card, telemetry_card, appearance_card]
        ThemeManager.instance().theme_changed.connect(self._apply_card_theme)
        self._apply_card_theme()

        appearance_content.addWidget(QLabel("Tema"))
        self._theme_combo = _NoScrollComboBox()
        for value, label in _THEMES:
            self._theme_combo.addItem(label, value)
        appearance_content.addWidget(self._theme_combo)
        self._theme_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        appearance_content.addSpacing(10)
        appearance_content.addWidget(QLabel("Arayüz Boyutu"))

        scale_row = QHBoxLayout()
        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setRange(80, 140)
        self._scale_slider.setValue(100)
        self._scale_slider.valueChanged.connect(self._on_scale_preview)
        scale_row.addWidget(self._scale_slider, stretch=1)
        self._scale_label = QLabel("100%")
        self._scale_label.setFixedWidth(40)
        scale_row.addWidget(self._scale_label)
        appearance_content.addLayout(scale_row)

        # ================= Kaydet =================
        self._save_button = QPushButton("KAYDET")
        self._save_button.setObjectName("PrimaryButton")
        self._save_button.setFixedHeight(44)
        self._save_button.clicked.connect(self._on_save)
        layout.addWidget(self._save_button)

        self._saved_banner = QLabel("✓ Ayarlar başarıyla kaydedildi")
        self._saved_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._saved_banner.setStyleSheet(
            f"background-color: {rgba(GREEN, 0.08)}; border: 1px solid {rgba(GREEN, 0.2)};"
            f"  border-radius: 10px; color: {GREEN}; font-size: 13px; font-weight: 500; padding: 10px;"
        )
        self._saved_banner.hide()
        layout.addWidget(self._saved_banner)

        layout.addStretch(1)

        self.refresh()

    def _apply_card_theme(self) -> None:
        """Ayarlar kartlarının arka planını canlı tema değerleriyle yeniden uygular."""
        for card in self._section_cards:
            card.setStyleSheet(
                f"QFrame {{ background-color: {theme_module.SURFACE};"
                f"  border: 1px solid {theme_module.BORDER}; border-radius: 16px; padding: 20px; }}"
            )
            
    def refresh(self) -> None:
        """Sayfa her gösterildiğinde profili DB'den yeniden yükler."""
        profile = self._profile_repo.get_current()
        if profile is None:
            self._udp_port_input.setValue(20777)
            return

        index = self._provider_combo.findData(profile.ai_provider)
        self._provider_combo.setCurrentIndex(index if index >= 0 else 0)

        self._udp_port_input.setValue(profile.udp_port)

        theme_index = self._theme_combo.findData(profile.theme)
        self._scale_slider.setValue(round(profile.ui_scale * 100))
        self._theme_combo.setCurrentIndex(theme_index if theme_index >= 0 else 0)

        self._load_api_key_for_current_provider()
        self._loaded_theme = profile.theme


    def _on_provider_changed(self) -> None:
        self._load_api_key_for_current_provider()

    def _on_scale_preview(self, value: int) -> None:
        self._scale_label.setText(f"{value}%")

    def _load_api_key_for_current_provider(self) -> None:
        provider = self._provider_combo.currentData()
        existing_key = get_api_key(provider)
        self._api_key_input.setText(existing_key)

    def _on_toggle_key_visibility(self) -> None:
        self._api_key_visible = not self._api_key_visible
        self._api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if self._api_key_visible else QLineEdit.EchoMode.Password
        )
        self._toggle_visibility_button.setText("🙈" if self._api_key_visible else "👁")

    def _on_save(self) -> None:
        profile = self._profile_repo.get_current()
        if profile is None:
            QMessageBox.warning(
                self, "Profil eksik",
                "Ayarları kaydetmeden önce lütfen Profil sayfasını tamamlayın.",
            )
            return

        provider = self._provider_combo.currentData()
        api_key = self._api_key_input.text().strip()

        profile.ai_provider = provider
        profile.udp_port = self._udp_port_input.value()
        profile.theme = self._theme_combo.currentData()
        profile.ui_scale = self._scale_slider.value() / 100.0
        self._profile_repo.save(profile)

        if api_key:
            save_api_key(provider, api_key)
        else:
            delete_api_key(provider)

        logger.info("Ayarlar kaydedildi: provider=%s udp_port=%d", provider, profile.udp_port)

        theme_manager = ThemeManager.instance()
        theme_manager.set_theme(profile.theme)
        theme_manager.set_scale(profile.ui_scale)
        self._saved_banner.setText("✓ Ayarlar başarıyla kaydedildi")

        self._saved_banner.show()
        QTimer.singleShot(3500, self._saved_banner.hide)

        self.settings_saved.emit()