"""ThemeManager — runtime tema ve ölçek değişikliklerini yöneten singleton.

theme.py'deki set_active_theme() modül seviyesi sabitleri günceller ama
kimseye haber vermez. ThemeManager bunun üzerine bir sinyal katmanı ekler:
tema veya ölçek değiştiğinde theme_changed yayınlanır, dinleyen her widget
kendi stilini yeniden hesaplayabilir — uygulamayı yeniden başlatmaya gerek
kalmadan.
"""

from PyQt6.QtCore import QObject, pyqtSignal

from f1_coach.presentation import theme as theme_module

_BASE_FONT_SIZE = 13


class ThemeManager(QObject):
    """Uygulama genelinde tek bir örneği olan tema/ölçek yöneticisi."""

    theme_changed = pyqtSignal()

    _instance: "ThemeManager | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._scale = 1.0

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    @property
    def scale(self) -> float:
        return self._scale

    def set_theme(self, theme_name: str) -> None:
        theme_module.set_active_theme(theme_name)
        self.theme_changed.emit()

    def set_scale(self, scale: float) -> None:
        self._scale = max(0.8, min(1.4, scale))
        self.theme_changed.emit()

    def base_font_size(self) -> int:
        return round(_BASE_FONT_SIZE * self._scale)

    def build_stylesheet(self) -> str:
        return theme_module.build_global_stylesheet(base_font_size=self.base_font_size())