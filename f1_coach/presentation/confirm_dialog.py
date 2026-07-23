"""ConfirmDialog — QMessageBox yerine kullanılan, tema sistemiyle tam uyumlu
basit bir onay penceresi.

QMessageBox'ın native buton alanı bazı Windows/Qt kombinasyonlarında
uygulamanın stylesheet'ini düzgün almıyor — buton metni görünmez hale
gelebiliyor. Bunun yerine sade bir QDialog + kendi QPushButton'larımızla
kurulan bu widget, diğer sayfalar gibi normal QWidget stillemesine tabi
olduğu için sorunu kökten çözüyor.
"""

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


def confirm(parent, title: str, message: str, confirm_text: str = "Evet", cancel_text: str = "Hayır") -> bool:
    """Basit bir Evet/Hayır onay penceresi gösterir, sonucu bool olarak döner."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(360)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(18)

    message_label = QLabel(message)
    message_label.setWordWrap(True)
    layout.addWidget(message_label)

    button_row = QHBoxLayout()
    button_row.addStretch(1)

    cancel_button = QPushButton(cancel_text)
    cancel_button.setObjectName("PrimaryButton")
    cancel_button.clicked.connect(dialog.reject)
    button_row.addWidget(cancel_button)

    confirm_button = QPushButton(confirm_text)
    confirm_button.setObjectName("PrimaryButton")
    confirm_button.setDefault(True)
    confirm_button.clicked.connect(dialog.accept)
    button_row.addWidget(confirm_button)

    layout.addLayout(button_row)

    return dialog.exec() == QDialog.DialogCode.Accepted

def notify(parent, title: str, message: str, button_text: str = "Tamam") -> None:
    """QMessageBox.warning/information yerine kullanılan tek butonlu bilgi penceresi."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(360)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(18)

    message_label = QLabel(message)
    message_label.setWordWrap(True)
    layout.addWidget(message_label)

    button_row = QHBoxLayout()
    button_row.addStretch(1)
    ok_button = QPushButton(button_text)
    ok_button.setObjectName("PrimaryButton")
    ok_button.setDefault(True)
    ok_button.clicked.connect(dialog.accept)
    button_row.addWidget(ok_button)
    layout.addLayout(button_row)

    dialog.exec()