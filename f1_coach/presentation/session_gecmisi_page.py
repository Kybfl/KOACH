"""Session Geçmişi ekranı — UI dokümanı §2.5.

Not: "Takım" filtresi UI dokümanında listelenmişti ama şu an session'a takım
bilgisi kaydetmiyoruz (bu, UDP Participants paketinin — Packet ID 4 — parse
edilmesini gerektirir, mevcut kapsamımızda yok). Bu yüzden yalnızca Pist,
Yıl, Hava Durumu filtreleri uygulanıyor.

Hava durumu artık Lap bazında tutulduğu için, kart üzerinde gösterilen ve
filtrelemede kullanılan değer session'daki en sık görülen hava durumudur —
yalnızca gösterim/filtreleme amaçlı, referans tur seçim mantığını etkilemez.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager
from f1_coach.domain.models.session import Session
from f1_coach.domain.ports.session_repository import SessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.parquet_writer import delete_session_files

logger = get_logger(__name__)

_ALL = "Tümü"


class SessionCard(QFrame):
    """Tek bir session'ı temsil eden kart.

    Signals:
        card_clicked:   Kartın herhangi bir yerine tıklandı (silme ikonu hariç).
        delete_clicked: Silme ikonuna tıklandı.
    """

    card_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_id = session.id
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
            "  border-radius: 10px; padding: 10px; }"
            "QFrame:hover { border: 1px solid #9B30FF; }"
        )

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)

        weather = session.dominant_weather
        best_lap = session.best_lap
        best_lap_text = f"{best_lap.lap_time:.3f}s" if best_lap else "—"

        info_layout = QVBoxLayout()
        title = QLabel(f"{session.track.display_name} — {session.session_type.display_name}")
        title.setStyleSheet("font-weight: 600; font-size: 14px; background: transparent; border: none;")
        info_layout.addWidget(title)

        subtitle_text = (
            f"{session.created_at.strftime('%d.%m.%Y')} · "
            f"{session.lap_count} tur · En iyi: {best_lap_text}"
        )
        if weather is not None:
            subtitle_text += f" · {weather.display_name}"
        subtitle = QLabel(subtitle_text)
        subtitle.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; background: transparent; border: none;")
        info_layout.addWidget(subtitle)

        layout.addLayout(info_layout, stretch=1)

        delete_button = QPushButton("🗑")
        delete_button.setFixedSize(28, 28)
        delete_button.setToolTip("Session'ı sil")
        delete_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background-color: rgba(255,255,255,0.08); border-radius: 6px; }"
        )
        delete_button.clicked.connect(lambda: self.delete_clicked.emit(self._session_id))
        layout.addWidget(delete_button)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.card_clicked.emit(self._session_id)
        super().mousePressEvent(event)


class SessionGecmisiPage(QWidget):
    """Filtrelenebilir session listesi.

    Signals:
        session_selected: Bir karta tıklandı, session_id taşır.
                          MainWindow bunu Lap Analizi'ne yönlendirmek için dinler.
    """

    session_selected = pyqtSignal(int)

    def __init__(self, session_repo: SessionRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_repo = session_repo
        self._all_sessions: list[Session] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        # --- Filtre çubuğu ---
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Pist:"))
        self._track_filter = QComboBox()
        filter_row.addWidget(self._track_filter)

        filter_row.addWidget(QLabel("Yıl:"))
        self._year_filter = QComboBox()
        filter_row.addWidget(self._year_filter)

        filter_row.addWidget(QLabel("Hava Durumu:"))
        self._weather_filter = QComboBox()
        filter_row.addWidget(self._weather_filter)

        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        for combo in (self._track_filter, self._year_filter, self._weather_filter):
            combo.currentIndexChanged.connect(self._apply_filters)

        # --- Kart listesi (kaydırılabilir) ---
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._card_container = QWidget()
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.addStretch(1)
        self._scroll_area.setWidget(self._card_container)
        layout.addWidget(self._scroll_area, stretch=1)

        self._empty_label = QLabel("Henüz kaydedilmiş session yok")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"font-size: 14px; color: {theme_module.TEXT_MUTED};")        
        layout.addWidget(self._empty_label)
        self._empty_label.hide()
        ThemeManager.instance().theme_changed.connect(self.refresh)


    def refresh(self) -> None:
        """Her gösterildiğinde tüm session'ları yeniden yükler."""
        self._all_sessions = self._session_repo.get_all()
        self._populate_filters()
        self._apply_filters()

    def _populate_filters(self) -> None:
        tracks = sorted({s.track.display_name for s in self._all_sessions})
        years = sorted({s.created_at.year for s in self._all_sessions}, reverse=True)
        weathers = sorted(
            {s.dominant_weather.display_name for s in self._all_sessions if s.laps}
        )

        for combo, values in (
            (self._track_filter, tracks),
            (self._year_filter, [str(y) for y in years]),
            (self._weather_filter, weathers),
        ):
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(_ALL)
            combo.addItems(values)
            index = combo.findText(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def _apply_filters(self) -> None:
        track = self._track_filter.currentText()
        year = self._year_filter.currentText()
        weather = self._weather_filter.currentText()

        filtered = self._all_sessions
        if track != _ALL:
            filtered = [s for s in filtered if s.track.display_name == track]
        if year != _ALL:
            filtered = [s for s in filtered if str(s.created_at.year) == year]
        if weather != _ALL:
            filtered = [
                s for s in filtered
                if s.laps and s.dominant_weather.display_name == weather
            ]

        self._render_cards(filtered)

    def _render_cards(self, sessions: list[Session]) -> None:
        while self._card_layout.count() > 1:
            item = self._card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._empty_label.setVisible(len(sessions) == 0)
        self._scroll_area.setVisible(len(sessions) > 0)

        for session in sessions:
            card = SessionCard(session)
            card.card_clicked.connect(self._on_card_clicked)
            card.delete_clicked.connect(self._on_delete_clicked)
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)

    def _on_card_clicked(self, session_id: int) -> None:
        self.session_selected.emit(session_id)

    def _on_delete_clicked(self, session_id: int) -> None:
        reply = QMessageBox.question(
            self, "Emin misin?",
            "Bu session ve tüm verileri kalıcı olarak silinecek. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        session = self._session_repo.get_by_id(session_id)
        if session is None:
            return

        self._session_repo.delete(session_id)
        delete_session_files(session.session_uid)
        logger.info("Session silindi: id=%d uid=%s", session_id, session.session_uid)

        self.refresh()