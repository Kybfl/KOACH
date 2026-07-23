"""TextPromptDialog — QInputDialog yerine kullanılan, tema sistemiyle
tam uyumlu basit bir metin girişi penceresi.

QInputDialog da QMessageBox gibi native buton alanı kullanır ve aynı
görünmez-buton sorununa maruz kalır — bkz. confirm_dialog.py.
"""

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


def prompt_text(parent, title: str, label: str, initial_text: str = "") -> str | None:
    """Basit bir metin girişi penceresi gösterir.

    Returns:
        Kullanıcı "Tamam" dediyse girilen metin (trim edilmiş, boş olabilir),
        "Vazgeç" dediyse ya da pencereyi kapattıysa None.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(360)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(14)

    label_widget = QLabel(label)
    label_widget.setWordWrap(True)
    layout.addWidget(label_widget)

    input_field = QLineEdit()
    input_field.setText(initial_text)
    layout.addWidget(input_field)

    button_row = QHBoxLayout()
    button_row.addStretch(1)

    cancel_button = QPushButton("Vazgeç")
    cancel_button.setObjectName("PrimaryButton")
    cancel_button.clicked.connect(dialog.reject)
    button_row.addWidget(cancel_button)

    ok_button = QPushButton("Tamam")
    ok_button.setObjectName("PrimaryButton")
    ok_button.setDefault(True)
    ok_button.clicked.connect(dialog.accept)
    button_row.addWidget(ok_button)

    layout.addLayout(button_row)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return input_field.text().strip()
    return None