"""QWebEngineView tabanlı, Plotly HTML'i render eden basit widget."""

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget


class PlotlyChartWidget(QWidget):
    """Plotly figürünü göstermek için tek metodu olan sarmalayıcı: render_html()."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._view = QWebEngineView()
        layout.addWidget(self._view)

    def render_html(self, html: str) -> None:
        self._view.setHtml(html)