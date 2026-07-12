"""Lap Analizi ekranı — UI dokümanı §2.4.

Katman 1 (LapTableWidget): sektör tablosu, mor en-iyi vurgusu.
Katman 2 (LapDetailWidget): Tek Lap / Karşılaştırmalı Lap sekmeleri.
LapAnaliziPage: ikisini QStackedWidget ile birleştiren konteyner.

AI butonları yalnızca coaching_engine sağlandıysa (Faz 6, Ayarlar'da API key
girildikten sonra) aktif olur; şimdilik None geçilir ve butonlar devre dışı
kalır, tooltip ile açıklanır.
"""
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.models.enums import TrackName
from f1_coach.presentation.theme import BORDER, SURFACE, TEXT_SECONDARY, rgba
from f1_coach.application.coaching_engine import CoachingEngine
from f1_coach.domain.models.lap import Lap
from f1_coach.domain.ports.lap_repository import LapRepository
from f1_coach.domain.ports.session_repository import SessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.parquet_writer import read_telemetry, read_positions
from f1_coach.presentation.charts.lap_chart_builder import (
    build_comparison_html,
    build_single_lap_html,
)
from f1_coach.presentation.charts.lap_chart_builder import (
    build_comparison_html,
    build_single_lap_html,
    build_track_map_html,
)
from f1_coach.presentation.charts.plotly_chart_widget import PlotlyChartWidget

logger = get_logger(__name__)

_F1_PURPLE = "#9B30FF"   

def _format_time(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}:{secs:06.3f}"


class LapTableWidget(QWidget):
    """Katman 1 — sektör tablosu.

    Signals:
        lap_selected: Bir tura tıklandı, lap_number taşır.
    """

    lap_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Tur", "S1", "S2", "S3", "Toplam"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.cellClicked.connect(self._on_cell_clicked)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._table)
        self._laps: list[Lap] = []

    def set_laps(self, laps: list[Lap]) -> None:
        self._laps = laps
        self._table.setRowCount(len(laps))

        valid_laps = [lap for lap in laps if lap.is_valid_reference]
        best_lap_number = min(valid_laps, key=lambda lap: lap.lap_time).lap_number if valid_laps else None
        best_s1 = min((lap.sector_1_time for lap in valid_laps), default=None)
        best_s2 = min((lap.sector_2_time for lap in valid_laps), default=None)
        best_s3 = min((lap.sector_3_time for lap in valid_laps), default=None)

        for row, lap in enumerate(laps):
            values = [
                str(lap.lap_number),
                f"{lap.sector_1_time:.3f}",
                f"{lap.sector_2_time:.3f}",
                f"{lap.sector_3_time:.3f}",
                _format_time(lap.lap_time),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if not lap.is_valid:
                    item.setForeground(Qt.GlobalColor.gray)
                elif lap.lap_number == best_lap_number:
                    item.setBackground(Qt.GlobalColor.transparent)
                    item.setForeground(Qt.GlobalColor.white)
                    item.setBackground(_purple_highlight())
                self._table.setItem(row, col, item)

            # Sektör bazlı mor vurgu (satır geneli mor değilse bile)
            if lap.is_valid_reference:
                if best_s1 is not None and lap.sector_1_time == best_s1:
                    item.setBackground(_purple_highlight())
                if best_s2 is not None and lap.sector_2_time == best_s2:
                    item.setBackground(_purple_highlight())
                if best_s3 is not None and lap.sector_3_time == best_s3:
                    item.setBackground(_purple_highlight())

    def _on_cell_clicked(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._laps):
            self.lap_selected.emit(self._laps[row].lap_number)


def _purple_highlight() -> QColor:
    """Sektör/tur en iyi rengi — %28 opaklıkta mor vurgu."""
    return QColor(155, 48, 255, 70)  # #9B30FF, alpha≈70/255


class LapDetailWidget(QWidget):
    """Katman 2 — seçilen turun detay analizi.

    Signals:
        back_pressed: "Geri" butonu — tabloya dönmek için.
    """

    back_pressed = pyqtSignal()

    def __init__(
        self,
        lap_repo: LapRepository,
        session_repo: SessionRepository,
        coaching_engine: CoachingEngine | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._lap_repo = lap_repo
        self._session_repo = session_repo
        self._coaching_engine = coaching_engine
        self._current_lap: Lap | None = None
        self._all_laps: list[Lap] = []
        self._track_id: int = -1

        layout = QVBoxLayout(self)

        header_row = QHBoxLayout()
        self._back_button = QPushButton("← Geri")
        self._back_button.clicked.connect(self.back_pressed.emit)
        header_row.addWidget(self._back_button)
        self._header_label = QLabel("")
        self._header_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        header_row.addWidget(self._header_label)
        layout.addLayout(header_row)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # --- Sekme 1: Tek Lap Analizi (tüm sayfa kaydırılabilir) ---
        single_scroll = QScrollArea()
        single_scroll.setWidgetResizable(True)
        single_content = QWidget()
        single_scroll.setWidget(single_content)
        single_layout = QVBoxLayout(single_content)
        self._single_chart = PlotlyChartWidget()
        self._single_chart.setFixedHeight(650)
        single_layout.addWidget(self._single_chart)

        self._single_ai_button = QPushButton("AI Analizi Oluştur")
        self._single_ai_button.clicked.connect(self._on_generate_single_feedback)
        single_layout.addWidget(self._single_ai_button)

        self._single_feedback_text = QTextEdit()
        self._single_feedback_text.setReadOnly(True)
        self._single_feedback_text.setMaximumHeight(160)
        single_layout.addWidget(self._single_feedback_text)

        self._tabs.addTab(single_scroll, "Tek Lap Analizi")

        # --- Sekme 2: Karşılaştırmalı Lap Analizi (tüm sayfa kaydırılabilir) ---
        compare_scroll = QScrollArea()
        compare_scroll.setWidgetResizable(True)
        compare_content = QWidget()
        compare_scroll.setWidget(compare_content)
        compare_layout = QVBoxLayout(compare_content)

        compare_row = QHBoxLayout()
        compare_row.addWidget(QLabel("Karşılaştırılacak tur:"))
        self._compare_combo = QComboBox()
        self._compare_combo.currentIndexChanged.connect(self._on_compare_lap_changed)
        compare_row.addWidget(self._compare_combo)
        compare_layout.addLayout(compare_row)

        self._compare_chart = PlotlyChartWidget()
        self._compare_chart.setFixedHeight(650)
        compare_layout.addWidget(self._compare_chart)

        self._track_map_label = QLabel("Pist Haritası (Demo)")
        self._track_map_label.setStyleSheet("font-size: 12px; font-weight: 600; margin-top: 8px;")
        compare_layout.addWidget(self._track_map_label)

        self._track_map_chart = PlotlyChartWidget()
        self._track_map_chart.setFixedHeight(550)
        compare_layout.addWidget(self._track_map_chart)

        self._compare_ai_button = QPushButton("AI Karşılaştırma Analizi Oluştur")
        self._compare_ai_button.clicked.connect(self._on_generate_comparison_feedback)
        compare_layout.addWidget(self._compare_ai_button)

        self._compare_feedback_text = QTextEdit()
        self._compare_feedback_text.setReadOnly(True)
        self._compare_feedback_text.setMaximumHeight(160)
        compare_layout.addWidget(self._compare_feedback_text)

        self._tabs.addTab(compare_scroll, "Karşılaştırmalı Lap Analizi")
        self._update_ai_button_state()

    def _update_ai_button_state(self) -> None:
        enabled = self._coaching_engine is not None
        tooltip = "" if enabled else "AI sağlayıcı henüz yapılandırılmadı (Ayarlar — Faz 6)"
        for button in (self._single_ai_button, self._compare_ai_button):
            button.setEnabled(enabled)
            button.setToolTip(tooltip)
    
    def set_coaching_engine(self, coaching_engine: CoachingEngine | None) -> None:
        """Ayarlar kaydedildiğinde MainWindow tarafından çağrılır."""
        self._coaching_engine = coaching_engine
        self._update_ai_button_state()

    def load_lap(self, lap: Lap, all_laps: list[Lap], track_id: int) -> None:
        self._current_lap = lap
        self._all_laps = all_laps
        self._track_id = track_id

        validity = "Geçerli" if lap.is_valid else "Geçersiz"
        self._header_label.setText(f"Tur {lap.lap_number} — {_format_time(lap.lap_time)} ({validity})")

        if lap.telemetry_file:
            df = read_telemetry(lap.telemetry_file)
            html = build_single_lap_html(df, f"Tur {lap.lap_number}")
            self._single_chart.render_html(html)

        self._single_feedback_text.clear()
        self._compare_feedback_text.clear()

        self._compare_combo.blockSignals(True)
        self._compare_combo.clear()
        for other in all_laps:
            if other.lap_number != lap.lap_number:
                self._compare_combo.addItem(f"Tur {other.lap_number}", other.lap_number)
        self._compare_combo.blockSignals(False)

        if self._compare_combo.count() > 0:
            self._compare_combo.setCurrentIndex(0)
            self._on_compare_lap_changed(0)

    def _on_compare_lap_changed(self, index: int) -> None:
        if index < 0 or self._current_lap is None or not self._current_lap.telemetry_file:
            return
        other_lap_number = self._compare_combo.itemData(index)
        other_lap = next(
            (lap for lap in self._all_laps if lap.lap_number == other_lap_number), None
        )
        if other_lap is None or not other_lap.telemetry_file:
            return

        label_a = f"Tur {self._current_lap.lap_number}"
        label_b = f"Tur {other_lap.lap_number}"

        df_a = read_telemetry(self._current_lap.telemetry_file)
        df_b = read_telemetry(other_lap.telemetry_file)
        html = build_comparison_html(df_a, df_b, label_a, label_b)
        self._compare_chart.render_html(html)

        if self._current_lap.position_file and other_lap.position_file:
            positions_a = read_positions(self._current_lap.position_file)
            positions_b = read_positions(other_lap.position_file)
            track = TrackName.from_udp(self._track_id)
            map_html = build_track_map_html(
                positions_a, positions_b, df_a, df_b, label_a, label_b, track=track
            )            
            self._track_map_chart.render_html(map_html)
            self._track_map_label.setVisible(True)
            self._track_map_chart.setVisible(True)
        else:
            # Bu turlar Motion paketi entegrasyonundan önce kaydedilmişse konum
            # verisi yok — harita alanını gizle, hata verme.
            self._track_map_label.setVisible(False)
            self._track_map_chart.setVisible(False)

    def _on_generate_single_feedback(self) -> None:
        if self._coaching_engine is None or self._current_lap is None:
            return
        try:
            feedback = self._coaching_engine.generate_post_lap_feedback(
                self._current_lap, self._current_lap.session_id, self._track_id
            )
            self._single_feedback_text.setPlainText(feedback.feedback_text)
        except Exception as exc:
            logger.error("AI feedback üretimi başarısız: %s", exc)
            self._single_feedback_text.setPlainText(f"Hata: {exc}")

    def _on_generate_comparison_feedback(self) -> None:
        if self._coaching_engine is None or self._current_lap is None:
            return
        other_lap_number = self._compare_combo.currentData()
        other_lap = next((lap for lap in self._all_laps if lap.lap_number == other_lap_number), None)
        if other_lap is None:
            return
        try:
            text = self._coaching_engine.generate_comparison_feedback(self._current_lap, other_lap)
            self._compare_feedback_text.setPlainText(text)
        except Exception as exc:
            logger.error("AI karşılaştırma feedback üretimi başarısız: %s", exc)
            self._compare_feedback_text.setPlainText(f"Hata: {exc}")


class LapAnaliziPage(QWidget):
    """Katman 1 + Katman 2'yi birleştiren konteyner."""

    def __init__(
        self,
        session_repo: SessionRepository,
        lap_repo: LapRepository,
        coaching_engine: CoachingEngine | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session_repo = session_repo
        self._lap_repo = lap_repo

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._empty_label = QLabel("Henüz session yok")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("font-size: 16px; color: #888;")

        self._stack = QStackedWidget()
        self._table_widget = LapTableWidget()
        self._table_widget.lap_selected.connect(self._on_lap_selected)
        self._detail_widget = LapDetailWidget(lap_repo, session_repo, coaching_engine)
        self._detail_widget.back_pressed.connect(self._show_table)

        self._page_empty = self._stack.addWidget(self._empty_label)
        self._page_table = self._stack.addWidget(self._table_widget)
        self._page_detail = self._stack.addWidget(self._detail_widget)

        layout.addWidget(self._stack)

        self._current_session_id: int | None = None
        self._current_track_id: int = -1
        self._all_laps: list[Lap] = []

    def refresh(self) -> None:
        """Her gösterildiğinde en son session'ı yükler (Canlı Session akışı için)."""
        sessions = self._session_repo.get_all()
        if not sessions:
            self._stack.setCurrentIndex(self._page_empty)
            return
        self.load_session(sessions[0].id)
    
    def set_coaching_engine(self, coaching_engine: CoachingEngine | None) -> None:
        self._detail_widget.set_coaching_engine(coaching_engine)

    def load_session(self, session_id: int) -> None:
        """Belirli bir session'ı yükler (Session Geçmişi'nden gelen seçim için)."""
        session = self._session_repo.get_by_id(session_id)
        if session is None or not session.laps:
            self._stack.setCurrentIndex(self._page_empty)
            return
        
        self._current_session_id = session.id
        self._current_track_id = session.track.value
        self._all_laps = session.laps

        self._table_widget.set_laps(self._all_laps)
        self._stack.setCurrentIndex(self._page_table)

    def _on_lap_selected(self, lap_number: int) -> None:
        lap = next((item for item in self._all_laps if item.lap_number == lap_number), None)
        if lap is None:
            return
        self._detail_widget.load_lap(lap, self._all_laps, self._current_track_id)
        self._stack.setCurrentIndex(self._page_detail)

    def _show_table(self) -> None:
        self._stack.setCurrentIndex(self._page_table)