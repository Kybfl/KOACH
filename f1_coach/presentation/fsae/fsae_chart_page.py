"""FSAEChartPage — Grafik sekmesi.

Etiketleme tamamlandıktan sonra decoded_telemetry Parquet dosyasından
kanalları okur, kullanıcının çoklu-seçim listesinden işaretlediği kanalları
tek bir grafikte gösterir. F1 25'in sabit panellerinin aksine kanal seti
session'a göre değiştiği için burada bir seçim listesi var.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.fsae.parquet_writer import read_decoded_telemetry
from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.banner_widget import WarningBanner
from f1_coach.presentation.charts.plotly_chart_widget import PlotlyChartWidget
from f1_coach.presentation.fsae.charts.fsae_chart_builder import build_multi_channel_html, compute_chart_height

logger = get_logger(__name__)

# Bu genişliğin altındaki pencerelerde büyütme önerisi gösterilir.
_MAXIMIZE_HINT_THRESHOLD_WIDTH = 1400

class FSAEChartPage(QWidget):
    """Seçilen kanalları grafikte gösteren ekran.

    Signals:
        session_finished: "Session'ı Bitir" butonuna basıldı. MainWindow
                          bunu dinleyip Ana Sayfa'ya döner.
    """

    session_finished = pyqtSignal()

    def __init__(
        self,
        vehicle_session_repo: VehicleSessionRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session_repo = vehicle_session_repo
        self._telemetry_df = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(14)

        self._header_label = QLabel("Grafik")
        self._header_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(self._header_label)

        self._maximize_banner = WarningBanner(
            "Grafikleri daha rahat inceleyebilmek için pencereyi büyütmeni öneririz.",
            "Büyüt",
        )
        self._maximize_banner.action_clicked.connect(self._on_maximize_clicked)
        layout.addWidget(self._maximize_banner)

        self._empty_label = QLabel(
            "Bu session için henüz çözümlenmiş veri yok — önce Etiketleme sekmesini tamamla."
        )
        self._empty_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(self._empty_label)

        content_row = QHBoxLayout()
        layout.addLayout(content_row, stretch=1)

        channel_column = QVBoxLayout()
        channel_label = QLabel("KANALLAR")
        channel_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        channel_column.addWidget(channel_label)

        self._channel_list = QListWidget()
        self._channel_list.setMaximumWidth(220)
        self._channel_list.itemChanged.connect(self._on_selection_changed)
        channel_column.addWidget(self._channel_list, stretch=1)

        content_row.addLayout(channel_column)

        self._chart = PlotlyChartWidget()
        chart_label = QLabel("GRAFİKLER")
        chart_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")

        chart_scroll = QScrollArea()
        chart_scroll.setWidgetResizable(True)
        chart_scroll.setFrameShape(QFrame.Shape.NoFrame)
        chart_scroll.setWidget(self._chart)
        content_row.addWidget(chart_scroll, stretch=1)

        self._finish_button = QPushButton("Session'ı Bitir")
        self._finish_button.setObjectName("PrimaryButton")
        self._finish_button.clicked.connect(self.session_finished.emit)
        layout.addWidget(self._finish_button)

        self._set_empty_state(True)

    def _set_empty_state(self, empty: bool) -> None:
        self._empty_label.setVisible(empty)
        self._channel_list.setVisible(not empty)
        self._chart.setVisible(not empty)
        self._finish_button.setVisible(not empty)
        if empty:
            self._maximize_banner.hide()

    def load_session(self, session_id: int) -> None:
        """MainWindow, Etiketleme tamamlandığında ya da bir session seçildiğinde çağırır."""
        session = self._session_repo.get_by_id(session_id)
        if session is None or not session.decoded_telemetry_file:
            self._set_empty_state(True)
            return

        self._header_label.setText(f"Grafik — {session.name}")
        self._telemetry_df = read_decoded_telemetry(session.decoded_telemetry_file)

        channels = sorted(self._telemetry_df["channel_name"].unique())

        self._channel_list.blockSignals(True)
        self._channel_list.clear()
        for channel in channels:
            item = QListWidgetItem(channel)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._channel_list.addItem(item)
        self._channel_list.blockSignals(False)

        self._set_empty_state(False)
        self._maybe_show_maximize_hint()
        self._render_chart()

    def _maybe_show_maximize_hint(self) -> None:
        window = self.window()
        already_large_enough = window.isMaximized() or window.width() >= _MAXIMIZE_HINT_THRESHOLD_WIDTH
        self._maximize_banner.setVisible(not already_large_enough)

    def _on_maximize_clicked(self) -> None:
        self.window().showMaximized()
        self._maximize_banner.hide()

    def _on_selection_changed(self, _item: QListWidgetItem) -> None:
        self._render_chart()

    def _selected_channels(self) -> list[str]:
        selected = []
        for row in range(self._channel_list.count()):
            item = self._channel_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def _render_chart(self) -> None:
        if self._telemetry_df is None:
            return
        selected = self._selected_channels()
        if not selected:
            self._chart.setFixedHeight(200)
            self._chart.render_html("<html><body></body></html>")
            return
        self._chart.setFixedHeight(compute_chart_height(len(selected)))
        html = build_multi_channel_html(self._telemetry_df, selected)
        self._chart.render_html(html)