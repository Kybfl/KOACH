"""Sarı bildirim banner'ı — eksik AI yapılandırması gibi durumlar için.

Tema değişiminde canlı güncellenir — renkler import anında değil, her
_apply_theme() çağrısında theme modülü üzerinden okunur.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager


class WarningBanner(QFrame):
    """Sarı çerçeveli, aksiyon butonlu bildirim çubuğu.

    Signals:
        action_clicked: Sağdaki buton tıklandı.
    """

    action_clicked = pyqtSignal()

    def __init__(self, message: str, action_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        self._message_label = QLabel(f"⚠ {message}")
        self._message_label.setWordWrap(True)
        layout.addWidget(self._message_label, stretch=1)

        self._action_button = QPushButton(action_text)
        self._action_button.clicked.connect(self.action_clicked.emit)
        layout.addWidget(self._action_button)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        yellow = theme_module.YELLOW
        # Yazı rengi kasıtlı olarak nötr gri — sarı zemin üstünde sarı yazı
        # okunmuyordu, TEXT_SECONDARY her iki temada da yeterli kontrast verir.
        self.setStyleSheet(
            "QFrame {"
            f"  background-color: {theme_module.rgba(yellow, 0.10)};"
            f"  border: 1px solid {theme_module.rgba(yellow, 0.3)};"
            "  border-radius: 10px;"
            "}"
        )
        self._message_label.setStyleSheet(
            f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
        )
        self._action_button.setStyleSheet(
            f"QPushButton {{ background-color: {yellow}; color: #0B0B0D; "
            "border: none; border-radius: 8px; padding: 6px 14px; "
            "font-size: 12px; font-weight: 600; }"
        )