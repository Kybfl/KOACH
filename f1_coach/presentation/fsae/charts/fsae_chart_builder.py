"""Plotly figürlerinden HTML üreten yardımcı fonksiyon — FSAE modülü.

Her seçili kanal KENDİ satırında, kendi otomatik ölçekli y-ekseninde
çizilir (paylaşılan x-ekseni ile). Tek bir ortak y-ekseninde üst üste
bindirmek, büyüklük mertebesi farklı kanalları (ör. batarya akımı ile
tekerlek hızı) karşılaştırılamaz hale getiriyordu — bu yüzden f125'in
lap_chart_builder.py'sindeki subplot deseni buraya da taşındı.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_COLOR_PALETTE = [
    "#9B30FF", "#00BFFF", "#2ecc71", "#e74c3c", "#f1c40f",
    "#FF8C00", "#1ABC9C", "#E91E63", "#3498DB", "#8BC34A",
]

_ROW_HEIGHT = 220
_CHART_MARGIN = 80


def compute_chart_height(num_channels: int) -> int:
    """Seçili kanal sayısına göre toplam grafik yüksekliğini hesaplar.

    fsae_chart_page.py bu değeri PlotlyChartWidget.setFixedHeight()'a da
    veriyor — QWebEngineView kendi içerik yüksekliğini Qt'ye geri
    raporlamadığı için, üretilen HTML'in gerçek yüksekliğiyle bu hesaplama
    senkron kalmalı.
    """
    if num_channels <= 0:
        return _ROW_HEIGHT
    return num_channels * _ROW_HEIGHT + _CHART_MARGIN


def _strip_internal_scroll(html: str) -> str:
    style_tag = "<style>html,body{margin:0;padding:0;overflow:hidden;}</style>"
    return html.replace("<head>", f"<head>{style_tag}", 1)


def build_multi_channel_html(telemetry_df: pd.DataFrame, selected_channels: list[str]) -> str:
    """Seçilen her kanalı kendi satırında, kendi ölçeğinde çizen grafik üretir.

    Args:
        telemetry_df:      read_decoded_telemetry() çıktısı — timestamp,
                           channel_name, value kolonları (long format).
        selected_channels: Grafiğe dahil edilecek kanal isimleri.

    Returns:
        QWebEngineView.setHtml() ile kullanılabilir tam HTML sayfası.
    """
    num_rows = len(selected_channels)
    if num_rows == 0:
        return "<html><body></body></html>"

    spacing = 0.08 if num_rows <= 1 else min(0.08, (1 / (num_rows - 1)) * 0.9)

    fig = make_subplots(
        rows=num_rows, cols=1, shared_xaxes=True,
        subplot_titles=selected_channels, vertical_spacing=spacing,
    )

    for index, channel in enumerate(selected_channels, start=1):
        channel_df = telemetry_df[telemetry_df["channel_name"] == channel].sort_values("timestamp")
        if channel_df.empty:
            continue
        color = _COLOR_PALETTE[(index - 1) % len(_COLOR_PALETTE)]
        fig.add_trace(
            go.Scatter(x=channel_df["timestamp"], y=channel_df["value"], name=channel, line=dict(color=color)),
            row=index, col=1,
        )

    fig.update_xaxes(title_text="Zaman (s)", row=num_rows, col=1)
    fig.update_layout(
        height=compute_chart_height(num_rows), showlegend=False,
        margin=dict(l=50, r=20, t=30, b=40), template="plotly_dark",
    )
    return _strip_internal_scroll(fig.to_html(include_plotlyjs="cdn", full_html=True))