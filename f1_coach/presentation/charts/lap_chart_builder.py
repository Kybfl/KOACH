"""Plotly figürlerinden HTML üreten yardımcı fonksiyonlar.

QWebEngineView, bu HTML'i doğrudan render eder. plotly.js CDN üzerinden
yüklenir — kullanıcının makinesinde internet bağlantısı gerektirir.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_PURPLE = "#9B30FF"   # F1 resmi en iyi sektör/tur rengi (UI dokümanı §3.3)
_COMPARISON_COLOR = "#00BFFF"


def _build_figure(traces_per_row: list[list[go.Scatter]], row_titles: list[str]) -> go.Figure:
    fig = make_subplots(
        rows=len(row_titles), cols=1, shared_xaxes=True,
        subplot_titles=row_titles, vertical_spacing=0.08,
    )
    for row_idx, traces in enumerate(traces_per_row, start=1):
        for trace in traces:
            fig.add_trace(trace, row=row_idx, col=1)
    fig.update_xaxes(title_text="Pist Pozisyonu", row=len(row_titles), col=1)
    fig.update_layout(
        height=650, showlegend=True,
        margin=dict(l=40, r=20, t=40, b=40),
        template="plotly_dark",
    )
    return fig


def build_single_lap_html(telemetry_df: pd.DataFrame, lap_label: str) -> str:
    """Tek tur için hız / gaz-fren / vites grafiklerini içeren HTML üretir."""
    x = telemetry_df["track_position"]

    speed_trace = [go.Scatter(x=x, y=telemetry_df["speed"], name=f"{lap_label} — Hız", line=dict(color=_PURPLE))]
    throttle_brake_traces = [
        go.Scatter(x=x, y=telemetry_df["throttle"] * 100, name="Gaz %", line=dict(color="#2ecc71")),
        go.Scatter(x=x, y=telemetry_df["brake"] * 100, name="Fren %", line=dict(color="#e74c3c")),
    ]
    gear_trace = [go.Scatter(x=x, y=telemetry_df["gear"], name="Vites", line=dict(color="#f1c40f", shape="hv"))]

    fig = _build_figure(
        [speed_trace, throttle_brake_traces, gear_trace],
        ["Hız (km/s)", "Gaz / Fren (%)", "Vites"],
    )
    return fig.to_html(include_plotlyjs="cdn", full_html=True)


def build_comparison_html(
    df_a: pd.DataFrame, df_b: pd.DataFrame, label_a: str, label_b: str
) -> str:
    """İki tur için üst üste bindirilmiş hız / gaz-fren grafiklerini üretir.

    Referans tur (A) mor, karşılaştırılan tur (B) farklı renkte gösterilir
    (UI dokümanı §2.4).
    """
    x_a, x_b = df_a["track_position"], df_b["track_position"]

    speed_traces = [
        go.Scatter(x=x_a, y=df_a["speed"], name=f"{label_a} — Hız", line=dict(color=_PURPLE)),
        go.Scatter(x=x_b, y=df_b["speed"], name=f"{label_b} — Hız", line=dict(color=_COMPARISON_COLOR)),
    ]
    throttle_traces = [
        go.Scatter(x=x_a, y=df_a["throttle"] * 100, name=f"{label_a} — Gaz %", line=dict(color=_PURPLE, dash="solid")),
        go.Scatter(x=x_b, y=df_b["throttle"] * 100, name=f"{label_b} — Gaz %", line=dict(color=_COMPARISON_COLOR, dash="solid")),
    ]
    brake_traces = [
        go.Scatter(x=x_a, y=df_a["brake"] * 100, name=f"{label_a} — Fren %", line=dict(color=_PURPLE, dash="dot")),
        go.Scatter(x=x_b, y=df_b["brake"] * 100, name=f"{label_b} — Fren %", line=dict(color=_COMPARISON_COLOR, dash="dot")),
    ]

    fig = _build_figure(
        [speed_traces, throttle_traces + brake_traces],
        ["Hız (km/s)", "Gaz / Fren (%)"],
    )
    return fig.to_html(include_plotlyjs="cdn", full_html=True)