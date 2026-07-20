"""Sidebar — Katman 1: dar, ikon bazlı, her zaman görünür sol panel.

Kullanıcının kendi SVG ikonları ve banner görseli assets/ klasöründen
yüklenir. Her ikon için gri (pasif) / renkli (hover) versiyon var — F1 25
butonu ise kare bir banner görseli olarak gösterilir (Sidebar.tsx'teki
"image" tipi nav öğesine karşılık gelir).
"""

from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout, QWidget

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme import ACCENT_RED, ORANGE, PURPLE, TEXT_PRIMARY
from f1_coach.presentation.theme_manager import ThemeManager
from f1_coach.presentation.resource_path import resource_path

_ICONS_DIR = resource_path("assets/icons")
_BANNER_DIR = resource_path("assets/banner")
_F125_BANNER = _BANNER_DIR / "f125-banner.jpg"
_FSAE_BANNER = _BANNER_DIR / "fsae-banner.png"
_SIDEBAR_WIDTH = 64

f125_path = Path(_F125_BANNER) if Path(_F125_BANNER).exists() else None
fsae_path = Path(_FSAE_BANNER) if Path(_FSAE_BANNER).exists() else None

def _make_cropped_rounded_pixmap(path: Path, size: int, corner_radius: int) -> QPixmap:
    """Verilen resmi kare olacak şekilde ortadan kırpar, köşeleri yuvarlar.

    CSS'teki object-fit:cover + border-radius davranışının Qt karşılığı.
    """
    source = QPixmap(str(path))
    if source.isNull():
        return QPixmap()

    source = source.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )

    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path_mask = QPainterPath()
    path_mask.addRoundedRect(0, 0, size, size, corner_radius, corner_radius)
    painter.setClipPath(path_mask)

    x_offset = (source.width() - size) // 2
    y_offset = (source.height() - size) // 2
    painter.drawPixmap(-x_offset, -y_offset, source)
    painter.end()

    return result


def _desaturate(pixmap: QPixmap) -> QPixmap:
    """Pasif durumda gösterilen gri tonlamalı versiyonu üretir."""
    if pixmap.isNull():
        return pixmap
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
    return QPixmap.fromImage(image)


class _NavIconButton(QToolButton):
    """Gri/renkli SVG çifti arasında hover'da geçiş yapan ikon butonu."""

    def __init__(self, gray_path: Path, color_path: Path, tooltip: str, accent: str) -> None:
        super().__init__()
        self._gray_icon = QIcon(str(gray_path)) if gray_path.exists() else QIcon()
        self._color_icon = QIcon(str(color_path)) if color_path.exists() else QIcon()
        self.setIcon(self._gray_icon)
        self.setIconSize(QSize(24, 24)) 
        self.setToolTip(tooltip)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        ThemeManager.instance().theme_changed.connect(self._apply_hover_theme)
        self._apply_hover_theme()

    def _apply_hover_theme(self) -> None:
        # TEXT_PRIMARY koyu temada açık, açık temada koyu renktir — hover her
        # zaman zemine göre görünür kalır (sabit beyazın aksine).
        hover_color = theme_module.rgba(theme_module.TEXT_PRIMARY, 0.10)
        self.setStyleSheet(
            "QToolButton { background-color: transparent; border: none; border-radius: 12px; }"
            f"QToolButton:hover {{ background-color: {hover_color}; }}"
    )
    

    def enterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.setIcon(self._color_icon)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.setIcon(self._gray_icon)
        super().leaveEvent(event)


class BannerButton(QFrame):
    """banner görseli, hover'da renkli + vurgu çerçeveli."""

    clicked = pyqtSignal()

    def __init__(self, banner_path: Path | None, accent: str) -> None:
        super().__init__()
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._label = QLabel(self)
        self._label.setGeometry(2, 2, 40, 40)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if banner_path is not None:
            base = _make_cropped_rounded_pixmap(banner_path, 40, 25)
            self._gray_pixmap: QPixmap | None = _desaturate(base)
            self._color_pixmap: QPixmap | None = base
            self._label.setPixmap(self._gray_pixmap)
        else:
            # Banner bulunamazsa eski emoji fallback'e dön — uygulama çökmesin.
            self._label.setText("🏎")
            self._gray_pixmap = None
            self._color_pixmap = None

        self._set_ring(False)

    def _set_ring(self, active: bool) -> None:
        if active:
            # Temadaki güncel vurgu/buton rengini modülden anlık olarak çekiyoruz
            current_accent = theme_module.ACCENT_RED
            self.setStyleSheet(
                f"QFrame {{ background-color: #000000; border: 2px solid {current_accent};"
                "  border-radius: 10px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background-color: transparent;"
                "  border: 1px solid rgba(245,245,247,0.08); border-radius: 10px; }"
            )

    def enterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._color_pixmap is not None:
            self._label.setPixmap(self._color_pixmap)
        self._set_ring(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._gray_pixmap is not None:
            self._label.setPixmap(self._gray_pixmap)
        self._set_ring(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.clicked.emit()
        super().mousePressEvent(event)

class _ProfileBadgeButton(QFrame):
    """Profil rozeti — fotoğraf yoksa isim baş harfi kırmızı kutuda, varsa
    dairesel kırpılmış fotoğraf gösterir. ProfilPage'de kayıt yapıldıkça
    set_profile() ile güncellenir.
    """

    clicked = pyqtSignal()

    def __init__(self, accent: str) -> None:
        super().__init__()
        self._accent = accent
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._label = QLabel(self)
        self._label.setGeometry(2, 2, 40, 40)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._photo_pixmap: QPixmap | None = None
        self.set_profile("", "")
        self._set_ring(False)

    def set_profile(self, name: str, photo_path: str) -> None:
        """Fotoğraf varsa daireselleştirip gösterir; yoksa isim baş harfini
        kırmızı zeminde gösterir (K logosuyla aynı görsel dil)."""
        if photo_path:
            pixmap = _make_cropped_rounded_pixmap(Path(photo_path), 40, 20)
            if not pixmap.isNull():
                self._photo_pixmap = pixmap
                self._label.setPixmap(pixmap)
                self._label.setStyleSheet("background: transparent;border: none;")
                return

        self._photo_pixmap = None
        initial = name.strip()[0].upper() if name.strip() else "?"
        self._label.setPixmap(QPixmap())
        self._label.setText(initial)
        self._label.setStyleSheet(
            "background-color: #E10600; border-radius: 20px;"
            "color: white; font-size: 16px; font-weight: 700;"
        )

    def _set_ring(self, active: bool) -> None:
        current_accent = theme_module.ACCENT_RED
        if active:
            self.setStyleSheet(f"QFrame {{ border: 2px solid {current_accent};; border-radius: 22px; background: transparent; }}")
        else:
            self.setStyleSheet("QFrame { border: 1px solid transparent; border-radius: 22px;background: transparent; }")

    def enterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._set_ring(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._set_ring(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.clicked.emit()
        super().mousePressEvent(event)

class Sidebar(QWidget):
    """Sabit genişlikte, dikey ikon şeridi.

    Signals:
        profile_clicked:  Üstteki avatar tıklandı → Profil sayfası.
        home_clicked:     Ana Sayfa ikonu tıklandı.
        f1_25_clicked:    F1 25 ikonu tıklandı → F1 25 Landing sayfası.
        fsae_clicked:     FSAE logosuna tıklandı -> FSAE landing sayfası.
        settings_clicked: Alttaki Ayarlar ikonu tıklandı.
    """

    profile_clicked = pyqtSignal()
    home_clicked = pyqtSignal()
    f1_25_clicked = pyqtSignal()
    fsae_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(_SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)  
        layout.setContentsMargins(8, 16, 8, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._profile_button = _ProfileBadgeButton(ACCENT_RED)

        self._profile_button.clicked.connect(self.profile_clicked.emit)
        layout.addWidget(self._profile_button)

        layout.addSpacing(8)

        self._home_button = _NavIconButton(
            _ICONS_DIR / "home-gray.svg", _ICONS_DIR / "home-color.svg", "Ana Sayfa", TEXT_PRIMARY
        )
        self._home_button.clicked.connect(self.home_clicked.emit)
        layout.addWidget(self._home_button)

        self._f1_25_button = BannerButton(f125_path, "#000000")
        self._f1_25_button.clicked.connect(self.f1_25_clicked.emit)
        layout.addWidget(self._f1_25_button)

        self._fsae_button = BannerButton(fsae_path, "#000000")
        self._fsae_button.clicked.connect(self.fsae_clicked.emit)
        layout.addWidget(self._fsae_button)

        layout.addStretch(1)

        self._settings_button = _NavIconButton(
            _ICONS_DIR / "settings-gray.svg", _ICONS_DIR / "settings-color.svg", "Ayarlar", TEXT_PRIMARY
        )
        self._settings_button.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self._settings_button)

    def set_navigation_locked(self, locked: bool) -> None:
        """Session kaydı sürerken sidebar'ı tamamen gizler.

        Devre dışı bırakıp gri göstermek yerine tamamen kaldırmak, "arka planda
        sessizce kayıt yapılıyor, dikkatini dağıtma" hissini daha net veriyor.
        """
        self.setVisible(not locked)

    def update_profile_badge(self, name: str, photo_path: str) -> None:
        """MainWindow tarafından açılışta ve her profil kaydından sonra çağrılır."""
        self._profile_button.set_profile(name, photo_path)