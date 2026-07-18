"""FSAELabelingPage — Etiketleme sekmesi.

Ham CAN frame'lerini elle etiketleme ekranı: distinct CAN ID'leri örnek
byte içerikleriyle listeler, kullanıcı her ID için bir veya daha fazla
sinyal tanımlar (byte aralığı + ölçek/offset + isim/birim). "Kaydet ve
Çözümle", mapping'leri DB'ye yazar ve channel_decoder.decode_telemetry ile
decoded_telemetry Parquet dosyasını üretir.

Mapping'ler session'a özel ve kalıcıdır — bu ekran her açıldığında o
session'ın mevcut mapping'lerini DB'den okuyup tabloya doldurur, kullanıcı
isterse düzeltip yeniden çözümleyebilir (orijinal CAN log dosyası tekrar
okunmaz, yalnızca raw_can_frames.parquet).
"""

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from f1_coach.application.fsae.channel_decoder import decode_telemetry
from f1_coach.domain.models.fsae.channel_mapping import ChannelMapping
from f1_coach.domain.models.fsae.vehicle_session import VehicleSession
from f1_coach.domain.ports.fsae.channel_mapping_repository import ChannelMappingRepository
from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.fsae.parquet_writer import (
    raw_can_frames_from_dataframe,
    read_raw_can_frames,
    write_decoded_telemetry,
)
from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager

logger = get_logger(__name__)


def _parse_can_id(text: str) -> int:
    """'0x123' veya '291' gibi kullanıcı girdisini int CAN ID'ye çevirir."""
    text = text.strip()
    return int(text, 16) if text.lower().startswith("0x") else int(text)


def _format_can_id(can_id: int) -> str:
    return f"0x{can_id:X}"


class FSAELabelingPage(QWidget):
    """Kanal etiketleme ekranı.

    Signals:
        decoding_completed: Çözümleme tamamlandı, session_id taşır.
                            MainWindow bunu dinleyip Grafik sekmesine geçebilir.
    """

    decoding_completed = pyqtSignal(int)

    def __init__(
        self,
        vehicle_session_repo: VehicleSessionRepository,
        channel_mapping_repo: ChannelMappingRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session_repo = vehicle_session_repo
        self._mapping_repo = channel_mapping_repo
        self._current_session: VehicleSession | None = None
        self._raw_frames_df: pd.DataFrame | None = None
        self._mappings: list[ChannelMapping] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(14)

        self._header_label = QLabel("Etiketleme")
        self._header_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(self._header_label)

        self._empty_label = QLabel("Önce İçe Aktar sekmesinden bir CAN log dosyası yükle.")
        self._empty_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(self._empty_label)

        # --- Bulunan CAN ID'ler (referans, salt okunur) ---
        self._ids_label = QLabel("BULUNAN CAN ID'LER")
        self._ids_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self._ids_label.hide()
        layout.addWidget(self._ids_label)

        self._ids_table = QTableWidget(0, 3)
        self._ids_table.setHorizontalHeaderLabels(["CAN ID", "Frame Sayısı", "Örnek Byte'lar"])
        self._ids_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._ids_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._ids_table.setMaximumHeight(180)
        self._ids_table.hide()
        layout.addWidget(self._ids_table)

        # --- Yeni kanal ekleme formu ---
        self._form_label = QLabel("YENİ KANAL EKLE")
        self._form_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self._form_label.hide()
        layout.addWidget(self._form_label)

        self._form_frame = QFrame()
        self._form_frame.hide()
        form_layout = QHBoxLayout(self._form_frame)

        self._can_id_input = QLineEdit()
        self._can_id_input.setPlaceholderText("CAN ID (0x123)")
        form_layout.addWidget(self._can_id_input)

        self._start_byte_input = QSpinBox()
        self._start_byte_input.setRange(0, 7)
        self._start_byte_input.setPrefix("byte ")
        form_layout.addWidget(self._start_byte_input)

        self._bit_length_input = QSpinBox()
        self._bit_length_input.setRange(1, 64)
        self._bit_length_input.setValue(16)
        self._bit_length_input.setSuffix(" bit")
        form_layout.addWidget(self._bit_length_input)

        self._endian_combo = QComboBox()
        self._endian_combo.addItems(["Little-endian", "Big-endian"])
        form_layout.addWidget(self._endian_combo)

        self._signed_checkbox = QCheckBox("İşaretli (signed)")
        form_layout.addWidget(self._signed_checkbox)

        self._scale_input = QDoubleSpinBox()
        self._scale_input.setRange(-1_000_000, 1_000_000)
        self._scale_input.setDecimals(6)
        self._scale_input.setValue(1.0)
        self._scale_input.setPrefix("× ")
        form_layout.addWidget(self._scale_input)

        self._offset_input = QDoubleSpinBox()
        self._offset_input.setRange(-1_000_000, 1_000_000)
        self._offset_input.setDecimals(6)
        self._offset_input.setPrefix("+ ")
        form_layout.addWidget(self._offset_input)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Kanal adı (ör. on_sol_tekerlek_hizi)")
        form_layout.addWidget(self._name_input, stretch=1)

        self._unit_input = QLineEdit()
        self._unit_input.setPlaceholderText("Birim (ör. km/s)")
        self._unit_input.setMaximumWidth(90)
        form_layout.addWidget(self._unit_input)

        self._add_mapping_button = QPushButton("Ekle")
        self._add_mapping_button.clicked.connect(self._on_add_mapping)
        form_layout.addWidget(self._add_mapping_button)

        layout.addWidget(self._form_frame)

        # --- Tanımlı kanallar tablosu ---
        self._mappings_label = QLabel("TANIMLI KANALLAR")
        self._mappings_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self._mappings_label.hide()
        layout.addWidget(self._mappings_label)

        self._mappings_table = QTableWidget(0, 9)
        self._mappings_table.setHorizontalHeaderLabels(
            ["CAN ID", "Başlangıç Byte", "Bit Uzunluğu", "Endian", "İşaretli",
             "Ölçek", "Offset", "İsim", "Birim"]
        )
        self._mappings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._mappings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._mappings_table.hide()
        layout.addWidget(self._mappings_table)

        self._remove_mapping_button = QPushButton("Seçili Kanalı Sil")
        self._remove_mapping_button.clicked.connect(self._on_remove_selected_mapping)
        self._remove_mapping_button.hide()
        layout.addWidget(self._remove_mapping_button)

        self._decode_button = QPushButton("Kaydet ve Çözümle")
        self._decode_button.setObjectName("PrimaryButton")
        self._decode_button.clicked.connect(self._on_decode)
        self._decode_button.hide()
        layout.addWidget(self._decode_button)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.hide()
        layout.addWidget(self._status_label)

        layout.addStretch(1)

    # ------------------------------------------------------------------
    # Yükleme
    # ------------------------------------------------------------------

    def load_session(self, session_id: int) -> None:
        """MainWindow, İçe Aktar tamamlandığında ya da bir session seçildiğinde çağırır."""
        session = self._session_repo.get_by_id(session_id)
        if session is None or not session.raw_can_file:
            self._show_empty_state()
            return

        self._current_session = session
        self._header_label.setText(f"Etiketleme — {session.name}")

        self._raw_frames_df = read_raw_can_frames(session.raw_can_file)
        self._populate_ids_table()

        self._mappings = self._mapping_repo.get_by_session(session.id)
        self._refresh_mappings_table()

        self._empty_label.hide()
        for widget in (
            self._ids_label, self._ids_table, self._form_label, self._form_frame,
            self._mappings_label, self._mappings_table, self._remove_mapping_button,
            self._decode_button,
        ):
            widget.show()
        self._status_label.hide()

    def _show_empty_state(self) -> None:
        self._current_session = None
        self._header_label.setText("Etiketleme")
        self._empty_label.show()
        for widget in (
            self._ids_label, self._ids_table, self._form_label, self._form_frame,
            self._mappings_label, self._mappings_table, self._remove_mapping_button,
            self._decode_button,
        ):
            widget.hide()

    def _populate_ids_table(self) -> None:
        if self._raw_frames_df is None or self._raw_frames_df.empty:
            self._ids_table.setRowCount(0)
            return

        grouped = self._raw_frames_df.groupby("can_id")
        summary = grouped.size().reset_index(name="count").sort_values("can_id")

        self._ids_table.setRowCount(len(summary))
        for row, record in enumerate(summary.itertuples(index=False)):
            sample = grouped.get_group(record.can_id).iloc[0]["data"]
            sample_hex = bytes(sample).hex(" ")
            self._ids_table.setItem(row, 0, QTableWidgetItem(_format_can_id(int(record.can_id))))
            self._ids_table.setItem(row, 1, QTableWidgetItem(str(record.count)))
            self._ids_table.setItem(row, 2, QTableWidgetItem(sample_hex))

    # ------------------------------------------------------------------
    # Mapping ekleme/silme
    # ------------------------------------------------------------------

    def _on_add_mapping(self) -> None:
        if self._current_session is None:
            return

        try:
            can_id = _parse_can_id(self._can_id_input.text())
        except ValueError:
            QMessageBox.warning(self, "Geçersiz CAN ID", "CAN ID '0x123' ya da '291' formatında olmalı.")
            return

        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "İsim eksik", "Kanal için bir isim girmelisin.")
            return

        mapping = ChannelMapping(
            session_id=self._current_session.id,
            can_id=can_id,
            start_byte=self._start_byte_input.value(),
            bit_length=self._bit_length_input.value(),
            little_endian=self._endian_combo.currentIndex() == 0,
            signed=self._signed_checkbox.isChecked(),
            scale=self._scale_input.value(),
            offset=self._offset_input.value(),
            name=name,
            unit=self._unit_input.text().strip(),
        )
        self._mappings.append(mapping)
        self._refresh_mappings_table()

        self._name_input.clear()
        self._unit_input.clear()

    def _on_remove_selected_mapping(self) -> None:
        row = self._mappings_table.currentRow()
        if row < 0 or row >= len(self._mappings):
            return
        removed = self._mappings.pop(row)
        if removed.is_persisted:
            self._mapping_repo.delete(removed.id)
        self._refresh_mappings_table()

    def _refresh_mappings_table(self) -> None:
        self._mappings_table.setRowCount(len(self._mappings))
        for row, mapping in enumerate(self._mappings):
            values = [
                _format_can_id(mapping.can_id),
                str(mapping.start_byte),
                str(mapping.bit_length),
                "Little" if mapping.little_endian else "Big",
                "Evet" if mapping.signed else "Hayır",
                f"{mapping.scale:g}",
                f"{mapping.offset:g}",
                mapping.name,
                mapping.unit,
            ]
            for col, value in enumerate(values):
                self._mappings_table.setItem(row, col, QTableWidgetItem(value))

    # ------------------------------------------------------------------
    # Kaydet ve Çözümle
    # ------------------------------------------------------------------

    def _on_decode(self) -> None:
        if self._current_session is None or self._raw_frames_df is None:
            return
        if not self._mappings:
            QMessageBox.warning(self, "Kanal yok", "Çözümlemeden önce en az bir kanal tanımlamalısın.")
            return

        for mapping in self._mappings:
            self._mapping_repo.save(mapping)

        frames = raw_can_frames_from_dataframe(self._raw_frames_df)
        points = decode_telemetry(frames, self._mappings)

        if not points:
            self._status_label.setStyleSheet(f"color: {theme_module.ACCENT_RED}; font-size: 12px;")
            self._status_label.setText(
                "⚠ Hiçbir kanal çözümlenemedi — CAN ID'lerin ve byte aralıklarının "
                "doğru olduğundan emin ol."
            )
            self._status_label.show()
            return

        session_identifier = Path(self._current_session.raw_can_file).parent.name
        decoded_path = write_decoded_telemetry(session_identifier, points)

        self._current_session.decoded_telemetry_file = decoded_path
        self._session_repo.save(self._current_session)

        distinct_channels = len({p.channel_name for p in points})
        self._status_label.setStyleSheet(f"color: {theme_module.GREEN}; font-size: 12px;")
        self._status_label.setText(f"✓ {len(points)} veri noktası, {distinct_channels} kanal çözümlendi.")
        self._status_label.show()

        logger.info(
            "FSAE session çözümlendi: id=%d points=%d channels=%d",
            self._current_session.id, len(points), distinct_channels,
        )
        self.decoding_completed.emit(self._current_session.id)