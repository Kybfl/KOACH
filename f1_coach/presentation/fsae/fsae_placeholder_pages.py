"""FSAE için geçici placeholder sayfalar.

Her biri, ilgili gerçek ekran (fsae_import_page.py, fsae_labeling_page.py,
fsae_chart_page.py) kodlandığında bu dosyadan silinip kendi modülüne
taşınacak — F1 25'in placeholder_pages.py'siyle aynı geçici amaç.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


def _make_placeholder(title: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    label = QLabel(title)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet("font-size: 20px; color: #888;")
    layout.addWidget(label)
    return widget


def make_fsae_import_placeholder() -> QWidget:
    return _make_placeholder("İçe Aktar (yapım aşamasında)")


def make_fsae_labeling_placeholder() -> QWidget:
    return _make_placeholder("Etiketleme (yapım aşamasında)")


def make_fsae_chart_placeholder() -> QWidget:
    return _make_placeholder("Grafik (yapım aşamasında)")