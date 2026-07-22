"""FSAESecondaryPanel — Katman 2: FSAE modülüne özel yatay sekme çubuğu.

secondary_panel.py'nin (F1 25) birebir aynı deseni, farklı sekmelerle:
İçe Aktar → Etiketleme → Grafik. Yalnızca FSAE Landing sayfasındaki
"Başla" butonuna basıldıktan sonra açılır.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

_PANEL_HEIGHT = 48


class FSAESecondaryPanel(QWidget):
    """FSAE sekmelerini barındıran yatay sekme çubuğu.

    Signals:
        import_clicked:    "İçe Aktar" sekmesi seçildi.
        labeling_clicked:  "Etiketleme" sekmesi seçildi.
        chart_clicked:     "Grafik" sekmesi seçildi.
    """

    import_clicked = pyqtSignal()
    labeling_clicked = pyqtSignal()
    chart_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(_PANEL_HEIGHT)
        self.setObjectName("SecondaryPanel")
        self.hide()  # Yalnızca "Başla" sonrası gösterilir.

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        self._import_button = QPushButton("İçe Aktar")
        self._import_button.setObjectName("PrimaryButton")
        self._import_button.clicked.connect(self.import_clicked.emit)
        layout.addWidget(self._import_button,1)

        self._labeling_button = QPushButton("Etiketleme")
        self._labeling_button.setObjectName("PrimaryButton")
        self._labeling_button.clicked.connect(self.labeling_clicked.emit)
        layout.addWidget(self._labeling_button,1)

        self._chart_button = QPushButton("Grafik")
        self._chart_button.setObjectName("PrimaryButton")
        self._chart_button.clicked.connect(self.chart_clicked.emit)
        layout.addWidget(self._chart_button,1)

        layout.addStretch(1)

    def open_panel(self) -> None:
        """FSAE Landing sayfasında "Başla"ya basıldığında çağrılır."""
        self.show()

    def close_panel(self) -> None:
        """Kullanıcı FSAE dışına çıktığında (ör. Ana Sayfa'ya dönünce) çağrılır."""
        self.hide()

    def set_navigation_locked(self, locked: bool) -> None:
        """İçe aktarma/etiketleme sürerken diğer sekmeleri kilitler.

        F1 25'teki canlı kayıt kilidinin karşılığı — burada "kayıt" yerine
        uzun sürebilecek bir dosya işleme/decode işlemi sırasında kullanılabilir.
        """
        self._labeling_button.setEnabled(not locked)
        self._chart_button.setEnabled(not locked)