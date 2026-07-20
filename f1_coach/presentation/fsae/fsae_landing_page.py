"""FSAE Landing sayfası — f125_landing_page.py'nin FSAE karşılığı.

Sol sidebar'daki FSAE logosuna her tıklamada gösterilir. Bu ekran
açıldığında ikincil panel henüz açılmaz — yalnızca "Başla" butonuna
basıldığında MainWindow.on_fsae_start_pressed() tetiklenir ve doğrudan
İçe Aktar sekmesine yönlendirir (F1 25'teki gibi arka planda başlayan bir
dinleyici yok; FSAE akışı tamamen kullanıcı tetiklemeli, offline bir
dosya işleme sürecidir).
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
    ("can_logs.svg", "GREEN", "Ham CAN Log İçe Aktarma",
     "Datalogger'dan USB ile alınan ham CAN log dosyasını (.blf/.asc/.trc/.csv) doğrudan içe aktar."),
    ("labeling.svg", "ORANGE", "Manuel Kanal Etiketleme",
     "Her CAN ID içindeki sinyalleri kendi elinle etiketle — ölçek, offset ve birim tanımla, DBC dosyasına ihtiyaç yok."),
    ("fsae_graph.svg", "BLUE", "Dinamik Kanal Grafikleri",
     "Session'a göre değişen kanal setinden istediğin sinyalleri seçip zaman bazlı grafiklerde incele."),
    ("edit.svg", "PURPLE", "Düzeltilebilir Etiketleme",
     "Yanlış etiketlediğin bir kanalı, dosyayı yeniden yüklemeden düzeltip anında yeniden çözümle."),
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


class FSAELandingPage(QWidget):
    """FSAE karşılama ekranı — yalnızca UI, backend'i başlatmaz.

    Signals:
        start_pressed: "Başla" butonuna basıldı. MainWindow bunu dinleyip
                       ikincil paneli açar ve İçe Aktar sekmesine geçer.
    """

    start_pressed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 56, 48, 48)
        layout.setSpacing(20)

        title = QLabel("FSAE Telemetri Analizi")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: 800;")
        layout.addWidget(title)

        subtitle = QLabel("Yarış sonrası datalogger verisini içe aktar, kanalları etiketle, analiz et.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 14px;")
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        self._grid = QGridLayout()
        self._grid.setSpacing(14)
        layout.addLayout(self._grid)

        layout.addStretch(1)

        self._start_button = QPushButton("Başla")
        self._start_button.setFixedHeight(48)
        self._start_button.setMinimumWidth(200)
        self._start_button.clicked.connect(self.start_pressed.emit)
        layout.addWidget(self._start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
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