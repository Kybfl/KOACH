"""F1 25 Landing sayfası — UI dokümanı §2.2, F1CoachingScreen.tsx görsel diline uyarlandı.

Sol sidebar'dan F1 25 ikonuna her tıklamada gösterilir. Bu ekran açıldığında
ikincil panel henüz açılmaz, backend (UDP dinleme) başlamaz — yalnızca
"Başla" butonuna basıldığında MainWindow.on_f1_25_start_pressed() tetiklenir.

Tema retrofit: kartlar ve rozet renkleri import anında sabitlenmez —
ThemeManager.theme_changed sinyaliyle _rebuild_feature_cards() her tema
değişiminde kartları theme modülünden okunan güncel renklerle yeniden kurar.
"""

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager

CURRENT_DIR = Path(__file__).resolve().parent.parent
ICONS_DIR = CURRENT_DIR / "assets" / "icons"

_FEATURE_CARDS = [
    ("udp.svg", "GREEN", "Gerçek Zamanlı UDP Telemetri Kaydı",
     "F1 25'in yayınladığı UDP verisini anlık olarak yakalar, her turda hız, fren, gaz ve direksiyon verisini kaydeder."),
    ("graph.svg", "BLUE", "Lap Delta ve Hız Trace Grafikleri",
     "Turlar arasındaki farkı görselleştir. Nerede zaman kazandın, nerede kaybettin — saniye saniye."),
    ("compare.svg", "ORANGE", "Fren / Gaz Overlay Analizi",
     "Fren noktalarını ve gaz uygulama profillerini bindirme grafiklerle karşılaştır."),
    ("feedback.svg", "PURPLE", "Session Sonrası AI Geri Bildirim",
     "Sürüşünü bulut tabanlı AI modeliyle analiz et. Kişiselleştirilmiş koçluk yorumları ve tur iyileştirme önerileri al."),
]


def _make_feature_card(icon_filename: str, color: str, title: str, description: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
        "  border-radius: 16px; padding: 18px; }"
    )
    layout = QVBoxLayout(card)

    icon_box = QLabel()
    icon_box.setFixedSize(70,70)
    icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setStyleSheet(
        f"background-color: {theme_module.rgba(color, 0.14)}; border-radius: 12px; font-size: 19px;"
    )
    # İkon dosyasını yükle ve 32x32'ye boyutlandır
    icon_path = ICONS_DIR / icon_filename
    if icon_path.exists():
        pixmap = QPixmap(str(icon_path))
        scaled_pixmap = pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        icon_box.setPixmap(scaled_pixmap)
    else:
        icon_box.setText("?")
        icon_box.setStyleSheet(icon_box.styleSheet() + " font-size: 20px; font-weight: bold;")

    # İkon kutusunu yatayda ortala
    layout.addWidget(icon_box, alignment=Qt.AlignmentFlag.AlignHCenter)

    title_label = QLabel(title)
    title_label.setWordWrap(True)
    title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    title_label.setStyleSheet("font-weight: 600; font-size: 14px; background: transparent;")
    layout.addWidget(title_label)

    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    desc_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    desc_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
    layout.addWidget(desc_label)

    return card


class F1_25LandingPage(QWidget):
    """F1 25 karşılama ekranı — yalnızca UI, backend'i başlatmaz.

    Signals:
        start_pressed: "Başla" butonuna basıldı. MainWindow bunu dinleyip
                       ikincil paneli açar ve Canlı Session'a geçer.
    """

    start_pressed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 56, 48, 48)
        layout.setSpacing(20)

        title = QLabel("F1 25 Koçluğu")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: 800;")
        layout.addWidget(title)

        subtitle = QLabel("Telemetri verisini gerçek zamanlı kaydet, AI destekli analizle sürüşünü bir üst seviyeye taşı.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 14px;")
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        # --- 2x2 özellik kartı grid'i ---
        self._grid = QGridLayout()
        self._grid.setSpacing(14)
        layout.addLayout(self._grid)

        layout.addStretch(1)

        # --- CTA butonu ---
        self._start_button = QPushButton("Başla")
        self._start_button.setFixedHeight(48)
        self._start_button.setMinimumWidth(200)
        self._start_button.clicked.connect(self.start_pressed.emit)
        layout.addWidget(self._start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Rozet, kartlar ve CTA butonunu güncel tema renkleriyle yeniden kurar."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        color_map = {
            "GREEN": theme_module.GREEN, "BLUE": theme_module.BLUE,
            "ORANGE": theme_module.ORANGE, "PURPLE": theme_module.PURPLE,
        }
        for index, (icon, color_key, card_title, desc) in enumerate(_FEATURE_CARDS):
            row, col = divmod(index, 2)
            self._grid.addWidget(
                _make_feature_card(icon, color_map[color_key], card_title, desc), row, col
            )

        self._start_button.setStyleSheet(
            "QPushButton {"
            "  background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            f"    stop:0 {theme_module.ACCENT_RED}, stop:1 {theme_module.ACCENT_RED_DARK});"
            f"  color: {theme_module.BUTTON_TEXT}; border: none; border-radius: 24px;"
            "  font-size: 15px; font-weight: 700;"
            "}"
            f"QPushButton:hover {{ background-color: {theme_module.ACCENT_RED_DARK}; }}"
        )