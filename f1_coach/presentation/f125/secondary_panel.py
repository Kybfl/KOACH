"""SecondaryPanel — Katman 2: yatay sekme çubuğu, F1 25'e özgü ikincil panel.

Yalnızca F1 25 Landing sayfasındaki "Başla" butonuna basıldıktan sonra açılır.
Yatay yerleşim, dikey sürüme göre içerik alanı için daha fazla genişlik bırakır
— özellikle Lap Analizi'ndeki grafikler için önemli.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

_PANEL_HEIGHT = 48


class SecondaryPanel(QWidget):
    """F1 25 sekmelerini barındıran yatay sekme çubuğu.

    Signals:
        live_session_clicked:  "Canlı Session" sekmesi seçildi.
        lap_analysis_clicked:  "Lap Analizi" sekmesi seçildi.
        session_history_clicked: "Session Geçmişi" sekmesi seçildi.
    """

    live_session_clicked = pyqtSignal()
    lap_analysis_clicked = pyqtSignal()
    session_history_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(_PANEL_HEIGHT)
        self.setObjectName("SecondaryPanel")
        self.hide()  # Yalnızca "Başla" sonrası gösterilir.

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        self._live_session_button = QPushButton("Canlı Session")
        self._live_session_button.clicked.connect(self.live_session_clicked.emit)
        layout.addWidget(self._live_session_button)

        self._lap_analysis_button = QPushButton("Lap Analizi")
        self._lap_analysis_button.clicked.connect(self.lap_analysis_clicked.emit)
        layout.addWidget(self._lap_analysis_button)

        self._session_history_button = QPushButton("Session Geçmişi")
        self._session_history_button.clicked.connect(self.session_history_clicked.emit)
        layout.addWidget(self._session_history_button)

        layout.addStretch(1)

    def open_panel(self) -> None:
        """F1 25 Landing sayfasında "Başla"ya basıldığında çağrılır."""
        self.show()

    def close_panel(self) -> None:
        """Kullanıcı F1 25 dışına çıktığında (ör. Ana Sayfa'ya dönünce) çağrılır."""
        self.hide()

    def set_navigation_locked(self, locked: bool) -> None:
        """Session kaydı sürerken Lap Analizi / Session Geçmişi sekmelerini kilitler."""
        self._lap_analysis_button.setEnabled(not locked)
        self._session_history_button.setEnabled(not locked)