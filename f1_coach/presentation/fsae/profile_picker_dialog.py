"""ProfilePickerDialog — kayıtlı etiketleme profillerinden birini seçtiren pencere."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

from f1_coach.domain.models.fsae.mapping_profile import MappingProfile


def pick_profile(parent, profiles: list[MappingProfile]) -> MappingProfile | None:
    """Var olan profillerden birini seçtiren pencere gösterir.

    Returns:
        Seçilen MappingProfile, ya da vazgeçildiyse None.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle("Profil Seç")
    dialog.setMinimumWidth(360)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(14)

    layout.addWidget(QLabel("Yüklemek istediğin profili seç:"))

    list_widget = QListWidget()
    for profile in profiles:
        item = QListWidgetItem(profile.name)
        item.setData(Qt.ItemDataRole.UserRole, profile)
        list_widget.addItem(item)
    list_widget.setCurrentRow(0)
    list_widget.itemDoubleClicked.connect(lambda _: dialog.accept())
    layout.addWidget(list_widget)

    button_row = QHBoxLayout()
    button_row.addStretch(1)
    cancel_button = QPushButton("Vazgeç")
    cancel_button.setObjectName("PrimaryButton")
    cancel_button.clicked.connect(dialog.reject)
    button_row.addWidget(cancel_button)
    select_button = QPushButton("Yükle")
    select_button.setObjectName("PrimaryButton")
    select_button.setDefault(True)
    select_button.clicked.connect(dialog.accept)
    button_row.addWidget(select_button)
    layout.addLayout(button_row)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        current = list_widget.currentItem()
        return current.data(Qt.ItemDataRole.UserRole) if current else None
    return None