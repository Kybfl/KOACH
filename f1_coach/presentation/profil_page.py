"""Profil sayfası — UI dokümanı §2.6, ProfileScreen.tsx görsel diline uyarlandı.

İki sütunlu grid: sol tarafta form (fotoğraf + kişisel bilgiler + F1 tercihleri),
sağ tarafta "Sürücü Özeti" kartı (takım rozeti + gerçek DB istatistikleri).

İki modda çalışır:
  - Onboarding modu: profil hiç yok, alanlar doğrudan düzenlenebilir,
    kaydedince onboarding_completed sinyali yayınlanır (MainWindow bunu
    Ana Sayfa'ya yönlendirmek için dinler).
  - Normal mod: profil var, alanlar salt-okunur başlar, "Düzenle" ile açılır.
"""

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager
from f1_coach.domain.models.enums import TrackName
from f1_coach.domain.models.profile import Profile
from f1_coach.domain.ports.profile_repository import ProfileRepository
from f1_coach.domain.ports.session_repository import SessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.presentation.theme import (
    BLUE,
    BORDER,
    GREEN,
    ORANGE,
    PURPLE,
    SURFACE,
    TEXT_MUTED,
    TEXT_SECONDARY,
    rgba,
)

logger = get_logger(__name__)

# Sabit dropdown listeleri — veri tutarlılığı için manuel giriş yok (UI dokümanı §2.6)
_TEAMS = [
    "Mercedes", "Ferrari", "Red Bull Racing", "Williams", "Aston Martin",
    "Alpine", "RB", "Haas", "McLaren", "Sauber",
]
_DRIVERS = [
    "Max Verstappen", "Yuki Tsunoda",
    "Charles Leclerc", "Lewis Hamilton",
    "George Russell", "Andrea Kimi Antonelli",
    "Lando Norris", "Oscar Piastri",
    "Fernando Alonso", "Lance Stroll",
    "Pierre Gasly", "Franco Colapinto",
    "Carlos Sainz", "Alex Albon",
    "Liam Lawson", "Isack Hadjar",
    "Esteban Ocon", "Oliver Bearman",
    "Nico Hulkenberg", "Gabriel Bortoleto",
]
_TRACKS = [track.display_name for track in TrackName if track != TrackName.UNKNOWN]

_TEAM_COLORS = {
    "Red Bull Racing": "#3671C6",
    "Ferrari": "#E10600",
    "Mercedes": "#27F4D2",
    "McLaren": "#FF8000",
    "Aston Martin": "#00665E",
    "Alpine": "#FF87BC",
    "Williams": "#64C4FF",
    "Haas": "#B6BABD",
    "Sauber": "#52E252",
    "RB": "#6692FF",
}
_DEFAULT_TEAM_COLOR = PURPLE


def _format_lap_time(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}:{secs:06.3f}"


def _make_circular_pixmap(path: str, size: int) -> QPixmap:
    """Verilen resmi, verilen boyutta dairesel kırpılmış bir QPixmap'e çevirir."""
    source = QPixmap(path)
    if source.isNull():
        return QPixmap()

    source = source.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )

    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path_mask = QPainterPath()
    path_mask.addEllipse(0, 0, size, size)
    painter.setClipPath(path_mask)

    x_offset = (source.width() - size) // 2
    y_offset = (source.height() - size) // 2
    painter.drawPixmap(-x_offset, -y_offset, source)
    painter.end()

    return result


def _make_stat_row(icon: str, label: str, value: str, color: str) -> QFrame:
    row = QFrame()
    row.setStyleSheet(f"QFrame {{ border-bottom: 1px solid {BORDER}; }}")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 8, 0, 8)

    icon_box = QLabel(icon)
    icon_box.setFixedSize(32, 32)
    icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setStyleSheet(
        f"background-color: {rgba(color, 0.14)}; border-radius: 9px; font-size: 14px;"
    )
    layout.addWidget(icon_box)

    label_widget = QLabel(label)
    label_widget.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;")
    layout.addWidget(label_widget, stretch=1)

    value_widget = QLabel(value)
    value_widget.setStyleSheet("font-size: 13px; font-weight: 600; background: transparent;")
    layout.addWidget(value_widget)

    return row


class ProfilPage(QWidget):
    """Profil formu — kişisel bilgiler, F1 tercihleri ve sürücü özeti.

    Signals:
        onboarding_completed: İlk kullanımda profil kaydedildi.
                              MainWindow bunu dinleyip Ana Sayfa'ya yönlendirir.
    """

    onboarding_completed = pyqtSignal()
    profile_saved = pyqtSignal()

    def __init__(
        self,
        profile_repo: ProfileRepository,
        session_repo: SessionRepository | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._profile_repo = profile_repo
        self._session_repo = session_repo
        self._is_onboarding = False
        self._photo_path = ""

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(32, 32, 32, 32)
        root_layout.setSpacing(20)

        # ================= SOL SÜTUN — form =================
        left_column = QVBoxLayout()
        left_column.setSpacing(16)
        root_layout.addLayout(left_column, stretch=3)

        # --- Fotoğraf alanı ---
        photo_row = QHBoxLayout()
        self._photo_label = QLabel("Fotoğraf yok")
        self._photo_label.setFixedSize(96, 96)
        self._photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._photo_label.setStyleSheet(
            "QLabel { border: 1px solid #555; border-radius: 48px; }"
        )
        photo_row.addWidget(self._photo_label)

        self._upload_button = QPushButton("Fotoğraf Yükle")
        self._upload_button.clicked.connect(self._on_upload_photo)
        photo_row.addWidget(self._upload_button)
        photo_row.addStretch(1)
        left_column.addLayout(photo_row)

        # --- Kişisel bilgiler ---
        form = QFormLayout()
        self._name_input = QLineEdit()
        self._email_input = QLineEdit()
        form.addRow("Ad Soyad:", self._name_input)
        form.addRow("E-posta:", self._email_input)
        left_column.addLayout(form)

        # --- F1 Tercihleri (dropdown, manuel giriş yok) ---
        pref_form = QFormLayout()
        self._team_combo = QComboBox()
        self._team_combo.addItems(_TEAMS)
        self._team_combo.currentTextChanged.connect(self._update_driver_summary)
        self._driver_combo = QComboBox()
        self._driver_combo.addItems(_DRIVERS)
        self._driver_combo.currentTextChanged.connect(self._update_driver_summary)
        self._track_combo = QComboBox()
        self._track_combo.addItems(_TRACKS)
        self._track_combo.currentTextChanged.connect(self._update_driver_summary)
        pref_form.addRow("Favori Takım:", self._team_combo)
        pref_form.addRow("Favori Pilot:", self._driver_combo)
        pref_form.addRow("Favori Pist:", self._track_combo)
        left_column.addLayout(pref_form)

        # --- Aksiyonlar ---
        action_row = QHBoxLayout()
        self._edit_button = QPushButton("Düzenle")
        self._edit_button.clicked.connect(self._enable_editing)
        self._save_button = QPushButton("Kaydet")
        self._save_button.clicked.connect(self._on_save)
        self._save_button.setStyleSheet(
            "QPushButton {"
            "  background-color: #16161A; color: #6B6B72;"
            "  border: 1px solid #26262B; border-radius: 10px;"
            "  padding: 8px 16px; font-weight: 600;"
            "}"
            "QPushButton:enabled {"
            "  background-color: #E10600; color: white; border: none;"
            "}"
            "QPushButton:enabled:hover { background-color: #A00400; }"
        )
        action_row.addWidget(self._edit_button)
        action_row.addWidget(self._save_button)
        action_row.addStretch(1)
        left_column.addLayout(action_row)

        left_column.addStretch(1)

        # ================= SAĞ SÜTUN — sürücü özeti =================
        self._right_card = QFrame()
        right_card = self._right_card
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(6)
        root_layout.addWidget(right_card, stretch=2)

        summary_header = QLabel("SÜRÜCÜ ÖZETİ")
        summary_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600; background: transparent;"
        )
        right_layout.addWidget(summary_header)

        self._team_badge = QFrame()
        badge_layout = QHBoxLayout(self._team_badge)
        badge_layout.setContentsMargins(12, 10, 12, 10)

        self._team_dot = QLabel()
        self._team_dot.setFixedSize(10, 10)
        badge_layout.addWidget(self._team_dot)

        badge_text_layout = QVBoxLayout()
        badge_text_layout.setSpacing(1)
        self._team_name_label = QLabel()
        self._team_name_label.setStyleSheet("font-size: 13px; font-weight: 600; background: transparent;")
        badge_text_layout.addWidget(self._team_name_label)
        self._driver_name_label = QLabel()
        self._driver_name_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;"
        )
        badge_text_layout.addWidget(self._driver_name_label)
        badge_layout.addLayout(badge_text_layout)
        badge_layout.addStretch(1)

        right_layout.addWidget(self._team_badge)

        self._stats_container = QVBoxLayout()
        self._stats_container.setSpacing(0)
        right_layout.addLayout(self._stats_container)

        note = QLabel("İstatistikler ilk session tamamlandıktan sonra otomatik güncellenir.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent; margin-top: 10px;")
        right_layout.addWidget(note)

        right_layout.addStretch(1)

        ThemeManager.instance().theme_changed.connect(self._apply_card_theme)
        self._apply_card_theme()

        self.refresh()

    def refresh(self) -> None:
        """Sayfa her gösterildiğinde profili DB'den yeniden yükler."""
        profile = self._profile_repo.get_current()
        self._is_onboarding = profile is None

        if profile is None:
            self._name_input.setText("")
            self._email_input.setText("")
            self._photo_path = ""
            self._apply_photo("")
            self._set_editable(True)
            self._edit_button.setEnabled(False)  # düzenlenecek bir şey yok henüz
        else:
            self._name_input.setText(profile.name)
            self._email_input.setText(profile.email)
            self._photo_path = profile.photo_path
            self._apply_photo(profile.photo_path)
            if profile.favorite_team in _TEAMS:
                self._team_combo.setCurrentText(profile.favorite_team)
            if profile.favorite_driver in _DRIVERS:
                self._driver_combo.setCurrentText(profile.favorite_driver)
            if profile.favorite_track in _TRACKS:
                self._track_combo.setCurrentText(profile.favorite_track)
            self._set_editable(False)
            self._edit_button.setEnabled(True)

        self._update_driver_summary()

    def _set_editable(self, editable: bool) -> None:
        self._name_input.setReadOnly(not editable)
        self._email_input.setReadOnly(not editable)
        self._team_combo.setEnabled(editable)
        self._driver_combo.setEnabled(editable)
        self._track_combo.setEnabled(editable)
        self._upload_button.setEnabled(editable)
        self._save_button.setEnabled(editable)

    def _apply_photo(self, path: str) -> None:
        """Verilen yoldaki resmi dairesel olarak _photo_label'a uygular."""
        if not path:
            self._photo_label.setText("Fotoğraf yok")
            self._photo_label.setPixmap(QPixmap())
            return
        pixmap = _make_circular_pixmap(path, 96)
        if pixmap.isNull():
            self._photo_label.setText("Fotoğraf yok")
            self._photo_label.setPixmap(QPixmap())
        else:
            self._photo_label.setText("")
            self._photo_label.setPixmap(pixmap)

    def _apply_card_theme(self) -> None:
        """Sağ sütun kartının rengini canlı tema değerleriyle yeniden uygular."""
        self._right_card.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.SURFACE};"
            f"  border: 1px solid {theme_module.BORDER}; border-radius: 16px; }}"
        )
        self._update_driver_summary()  # takım rozeti + istatistik satırlarını da tazeler
    
    def _update_driver_summary(self) -> None:
        """Sağ sütundaki takım rozetini ve istatistikleri günceller."""
        team = self._team_combo.currentText()
        driver = self._driver_combo.currentText()
        track = self._track_combo.currentText()
        color = _TEAM_COLORS.get(team, _DEFAULT_TEAM_COLOR)

        self._team_badge.setStyleSheet(
            f"QFrame {{ background-color: {rgba(color, 0.10)};"
            f"  border: 1px solid {rgba(color, 0.3)}; border-radius: 12px; }}"
        )
        self._team_dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self._team_name_label.setText(team)
        self._driver_name_label.setText(driver)

        while self._stats_container.count():
            item = self._stats_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_sessions = "—"
        best_lap_text = "—"
        if self._session_repo is not None:
            sessions = self._session_repo.get_all()
            total_sessions = str(len(sessions))
            all_best_laps = [s.best_lap for s in sessions if s.best_lap is not None]
            if all_best_laps:
                best_lap_text = _format_lap_time(min(lap.lap_time for lap in all_best_laps))

        self._stats_container.addWidget(
            _make_stat_row("🏁", "Toplam Session", total_sessions, BLUE)
        )
        self._stats_container.addWidget(
            _make_stat_row("⏱", "En İyi Tur", best_lap_text, GREEN)
        )
        self._stats_container.addWidget(
            _make_stat_row("🏆", "Favori Pist", track, ORANGE)
        )

    def _enable_editing(self) -> None:
        self._set_editable(True)

    def _on_upload_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Fotoğraf Seç", "", "Resimler (*.png *.jpg *.jpeg)"
        )
        if path:
            self._photo_path = path
            self._apply_photo(self._photo_path)

    def _on_save(self) -> None:
        existing = self._profile_repo.get_current()
        profile = Profile(
            name=self._name_input.text().strip(),
            email=self._email_input.text().strip(),
            favorite_team=self._team_combo.currentText(),
            favorite_driver=self._driver_combo.currentText(),
            favorite_track=self._track_combo.currentText(),
            photo_path=self._photo_path,
            id=existing.id if existing else -1,
            created_at=existing.created_at if existing else datetime.now(),
        )
        self._profile_repo.save(profile)
        logger.info("Profil kaydedildi: %s", profile.name)

        self._set_editable(False)
        self._edit_button.setEnabled(True)

        self.profile_saved.emit()

        if self._is_onboarding:
            self._is_onboarding = False
            self.onboarding_completed.emit()
