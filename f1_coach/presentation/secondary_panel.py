"""SecondaryPanel — Katman 2: kayar, F1 25'e özgü ikincil panel.

Claude.ai'daki sohbet geçmişi paneli gibi davranır: yalnızca F1 25 Landing
sayfasındaki "Başla" butonuna basıldıktan sonra açılır, kapandığında içerik
alanı tam genişliğe yayılır. Bu widget varsayılan olarak gizlidir —
MainWindow, "Başla" sinyali geldiğinde show() çağırır.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

_PANEL_WIDTH = 220


class SecondaryPanel(QWidget):
    """F1 25 sekmelerini barındıran kayar panel.

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
        self.setFixedWidth(_PANEL_WIDTH)
        self.setObjectName("SecondaryPanel")
        self.hide()  # Yalnızca "Başla" sonrası gösterilir.

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
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
        """Session kaydı sürerken Lap Analizi / Session Geçmişi sekmelerini kilitler.

        Canlı Session sekmesi kilitlenmez — zaten üzerinde bulunulan ekran.
        """
        self._lap_analysis_button.setEnabled(not locked)
        self._session_history_button.setEnabled(not locked)