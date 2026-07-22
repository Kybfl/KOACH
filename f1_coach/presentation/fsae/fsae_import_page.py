"""FSAEImportPage — İçe Aktar sekmesi.

Ham CAN log dosyasını seçtirir, CanLogReader ile okur, raw frame'leri
Parquet'e yazar, bir VehicleSession olarak SQLite'a kaydeder. Decode
işlemi burada YAPILMAZ — bu sayfa yalnızca ham veriyi güvenli şekilde
diske/DB'ye yerleştirir; kanal etiketleme ve çözümleme Etiketleme
sekmesinin işi (bkz. fsae_labeling_page.py, henüz yazılmadı).

Şu an senkron çalışıyor (F1 25'teki AI feedback üretimi gibi) — çok büyük
log dosyalarında arayüz kısa süreliğine kilitlenebilir. İleride gerekirse
bir arka plan thread'ine taşınabilir; şimdilik kapsam dışı bırakıldı.
"""

import uuid
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.models.fsae.vehicle_session import VehicleSession
from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.infrastructure.fsae_can.can_log_reader_impl import PythonCanLogReader
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.fsae.parquet_writer import write_raw_can_frames
from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager

logger = get_logger(__name__)

_LOG_FILE_FILTER = (
    "CAN Log Dosyaları (*.asc *.blf *.csv *.db *.log *.trc *.mf4 *.gz);;"
    "Tüm Dosyalar (*)"
)


class FSAEImportPage(QWidget):
    """Ham CAN log dosyasını içe aktarma ekranı.

    Signals:
        session_imported: İçe aktarma başarıyla tamamlandı, session_id taşır.
                          MainWindow bunu dinleyip Etiketleme sekmesine o
                          session'ı önceden yüklü olarak geçebilir.
    """

    session_imported = pyqtSignal(int)

    def __init__(
        self,
        vehicle_session_repo: VehicleSessionRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session_repo = vehicle_session_repo
        self._can_reader = PythonCanLogReader()
        self._selected_file_path: str = ""
        self._last_imported_session_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("İçe Aktar")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Datalogger'dan USB ile alınan ham CAN log dosyasını seç — "
            "kanal etiketlemesi bir sonraki adımda yapılacak."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(subtitle)

        # --- Dosya seçimi ---
        file_row = QHBoxLayout()
        self._select_file_button = QPushButton("Dosya Seç")
        self._select_file_button.setObjectName("PrimaryButton")
        self._select_file_button.clicked.connect(self._on_select_file)
        file_row.addWidget(self._select_file_button)

        self._file_label = QLabel("Henüz dosya seçilmedi")
        self._file_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        file_row.addWidget(self._file_label, stretch=1)
        layout.addLayout(file_row)

        # --- Session adı ---
        layout.addWidget(QLabel("Session Adı"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("örn. Endurance - 14.07.2026")
        layout.addWidget(self._name_input)

        # --- İçe aktar butonu ---
        self._import_button = QPushButton("İçe Aktar")
        self._import_button.setObjectName("PrimaryButton")
        self._import_button.setEnabled(False)
        self._import_button.clicked.connect(self._on_import)
        layout.addWidget(self._import_button)

        # --- Durum / hata mesajı ---
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.hide()
        layout.addWidget(self._status_label)

        # --- Sonuç kartı ---
        self._result_card = QFrame()
        self._result_card.hide()
        result_layout = QVBoxLayout(self._result_card)
        self._result_title = QLabel("")
        self._result_title.setStyleSheet("font-weight: 600; font-size: 14px;")
        result_layout.addWidget(self._result_title)
        self._result_detail = QLabel("")
        self._result_detail.setWordWrap(True)
        self._result_detail.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        result_layout.addWidget(self._result_detail)
        self._go_to_labeling_button = QPushButton("Etiketlemeye Geç")
        self._go_to_labeling_button.setObjectName("PrimaryButton")
        self._go_to_labeling_button.clicked.connect(self._on_go_to_labeling)
        result_layout.addWidget(self._go_to_labeling_button)
        layout.addWidget(self._result_card)

        layout.addStretch(1)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self._result_card.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.rgba(theme_module.GREEN, 0.08)};"
            f"  border: 1px solid {theme_module.rgba(theme_module.GREEN, 0.2)}; border-radius: 12px; padding: 16px; }}"
        )

    def _on_select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "CAN Log Dosyası Seç", "", _LOG_FILE_FILTER)
        if not path:
            return

        self._selected_file_path = path
        self._file_label.setText(Path(path).name)
        self._file_label.setStyleSheet("font-size: 12px;")

        if not self._name_input.text().strip():
            self._name_input.setText(Path(path).stem)

        self._import_button.setEnabled(True)
        self._status_label.hide()
        self._result_card.hide()

    def _on_import(self) -> None:
        if not self._selected_file_path:
            return

        name = self._name_input.text().strip() or Path(self._selected_file_path).stem

        self._status_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        self._status_label.setText("Dosya okunuyor...")
        self._status_label.show()
        self._result_card.hide()
        self._import_button.setEnabled(False)
        self.repaint()  # senkron işlem öncesi durum mesajını hemen göster

        try:
            frames = self._can_reader.read_frames(self._selected_file_path)
        except ValueError as exc:
            logger.error("CAN log okunamadı: %s", exc)
            self._show_error(f"Dosya okunamadı: {exc}")
            return

        session_identifier = uuid.uuid4().hex
        try:
            raw_can_file = write_raw_can_frames(session_identifier, frames)
        except ValueError as exc:
            logger.error("Ham CAN frame'leri yazılamadı: %s", exc)
            self._show_error(f"Veri diske yazılamadı: {exc}")
            return

        session = VehicleSession(
            name=name,
            source_filename=Path(self._selected_file_path).name,
            raw_can_file=raw_can_file,
        )
        self._session_repo.save(session)

        distinct_ids = len({f.can_id for f in frames})
        self._status_label.hide()
        self._result_title.setText(f"✓ \"{session.name}\" içe aktarıldı")
        self._result_detail.setText(
            f"{len(frames)} ham CAN frame'i, {distinct_ids} farklı CAN ID bulundu. "
            "Kanalları etiketlemek için devam et."
        )
        self._result_card.show()
        self._import_button.setEnabled(True)

        self._last_imported_session_id = session.id
        logger.info(
            "FSAE session içe aktarıldı: id=%d name=%s frames=%d distinct_ids=%d",
            session.id, session.name, len(frames), distinct_ids,
        )

    def _show_error(self, message: str) -> None:
        self._status_label.setStyleSheet(f"color: {theme_module.ACCENT_RED}; font-size: 12px;")
        self._status_label.setText(f"⚠ {message}")
        self._status_label.show()
        self._import_button.setEnabled(True)

    def _on_go_to_labeling(self) -> None:
        if self._last_imported_session_id is not None:
            self.session_imported.emit(self._last_imported_session_id)