"""Geçici placeholder sayfalar.

Her biri, ilgili gerçek ekran kodlandığında bu dosyadan silinip kendi
modülüne taşınacak. Şimdilik navigasyon iskeletinin uçtan uca test
edilebilmesi için buradalar.
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


def make_ana_sayfa_placeholder() -> QWidget:
    return _make_placeholder("Ana Sayfa (yapım aşamasında)")


def make_f1_25_landing_placeholder() -> QWidget:
    return _make_placeholder("F1 25 Landing (yapım aşamasında)")


def make_profil_placeholder() -> QWidget:
    return _make_placeholder("Profil (yapım aşamasında)")


def make_ayarlar_placeholder() -> QWidget:
    return _make_placeholder("Ayarlar (Faz 6'da eklenecek)")


def make_canli_session_placeholder() -> QWidget:
    return _make_placeholder("Canlı Session (yapım aşamasında)")


def make_lap_analizi_placeholder() -> QWidget:
    return _make_placeholder("Lap Analizi (yapım aşamasında)")


def make_session_gecmisi_placeholder() -> QWidget:
    return _make_placeholder("Session Geçmişi (yapım aşamasında)")
