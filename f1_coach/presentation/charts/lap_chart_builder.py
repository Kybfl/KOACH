"""Plotly figürlerinden HTML üreten yardımcı fonksiyonlar.

QWebEngineView, bu HTML'i doğrudan render eder. plotly.js CDN üzerinden
yüklenir — kullanıcının makinesinde internet bağlantısı gerektirir.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from f1_coach.domain.models.enums import TrackName

_PURPLE = "#9B30FF"   # F1 resmi en iyi sektör/tur rengi (UI dokümanı §3.3)
_COMPARISON_COLOR = "#00BFFF"

def _strip_internal_scroll(html: str) -> str:
    """Plotly'nin ürettiği HTML sayfasının kendi içinde scrollbar göstermesini
    engeller — dıştaki QScrollArea tek scroll kaynağı olsun diye."""
    style_tag = "<style>html,body{margin:0;padding:0;overflow:hidden;}</style>"
    return html.replace("<head>", f"<head>{style_tag}", 1)

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
    return _strip_internal_scroll(fig.to_html(include_plotlyjs="cdn", full_html=True))

def _compute_delta_trace(
    df_a: pd.DataFrame, df_b: pd.DataFrame, label_a: str, label_b: str
) -> go.Scatter:
    """Pist pozisyonuna göre B turunun A turuna göre zaman farkını hesaplar.

    Her iki turun telemetri örnekleri farklı pist pozisyonlarında alınmış
    olabileceği için, ortak bir pozisyon ızgarasına (0.0–1.0, 500 nokta)
    interpolasyonla eşleniyor.
    """
    grid = np.linspace(0.0, 1.0, 500)

    elapsed_a = (df_a["timestamp"] - df_a["timestamp"].min()).to_numpy()
    elapsed_b = (df_b["timestamp"] - df_b["timestamp"].min()).to_numpy()

    order_a = df_a["track_position"].to_numpy().argsort()
    order_b = df_b["track_position"].to_numpy().argsort()

    time_a_on_grid = np.interp(
        grid, df_a["track_position"].to_numpy()[order_a], elapsed_a[order_a]
    )
    time_b_on_grid = np.interp(
        grid, df_b["track_position"].to_numpy()[order_b], elapsed_b[order_b]
    )

    delta = time_b_on_grid - time_a_on_grid

    return go.Scatter(
        x=grid, y=delta,
        name=f"{label_b} − {label_a}",
        line=dict(color="#FFD700"),
        fill="tozeroy",
    )

def build_comparison_html(
    df_a: pd.DataFrame, df_b: pd.DataFrame, label_a: str, label_b: str
) -> str:
    """İki tur için üst üste bindirilmiş hız / gaz-fren grafiklerini,
    ve pist pozisyonuna göre aralarındaki zaman farkını (delta) üretir.

    Referans tur (A) mor, karşılaştırılan tur (B) farklı renkte gösterilir
    (UI dokümanı §2.4).
    """
    x_a, x_b = df_a["track_position"], df_b["track_position"]

    speed_traces = [
        go.Scatter(x=x_a, y=df_a["speed"], name=f"{label_a} — Hız", line=dict(color=_PURPLE)),
        go.Scatter(x=x_b, y=df_b["speed"], name=f"{label_b} — Hız", line=dict(color=_COMPARISON_COLOR)),
    ]
    throttle_traces = [
        go.Scatter(
            x=x_a, y=df_a["throttle"] * 100, name=f"{label_a} — Gaz %",
            line=dict(color=_PURPLE, dash="solid"),
        ),
        go.Scatter(
            x=x_b, y=df_b["throttle"] * 100, name=f"{label_b} — Gaz %",
            line=dict(color=_COMPARISON_COLOR, dash="solid"),
        ),
    ]
    brake_traces = [
        go.Scatter(
            x=x_a, y=df_a["brake"] * 100, name=f"{label_a} — Fren %",
            line=dict(color=_PURPLE, dash="dot"),
        ),
        go.Scatter(
            x=x_b, y=df_b["brake"] * 100, name=f"{label_b} — Fren %",
            line=dict(color=_COMPARISON_COLOR, dash="dot"),
        ),
    ]
    delta_trace = [_compute_delta_trace(df_a, df_b, label_a, label_b)]

    fig = _build_figure(
        [speed_traces, throttle_traces + brake_traces, delta_trace],
        ["Hız (km/s)", "Gaz / Fren (%)", "Zaman Farkı (s)"],
    )
    return _strip_internal_scroll(fig.to_html(include_plotlyjs="cdn", full_html=True))

def build_track_map_html(
    positions_a: pd.DataFrame,
    positions_b: pd.DataFrame,
    telemetry_a: pd.DataFrame,
    telemetry_b: pd.DataFrame,
    label_a: str,
    label_b: str,
    track: TrackName | None = None,
) -> str:
    """İki turun pist üzerindeki yolunu (racing line) üst üste çizer.

    Pist SVG'si, sürülen turun kendi konum verisinden otomatik hesaplanan
    bir sınır kutusuna göre, X ve Z için AYNI ölçekle (uniform scale)
    yerleştirilir — eksenler ayrı ayrı ölçeklenirse virajlar yamuk/eliptik
    görünür, bu yüzden tek ortak ölçek şart.
    """
    def _with_speed(positions: pd.DataFrame, telemetry: pd.DataFrame) -> pd.DataFrame:
        positions = positions.sort_values("track_position")
        telemetry = telemetry.sort_values("track_position")
        return pd.merge_asof(
            positions, telemetry[["track_position", "speed"]],
            on="track_position", direction="nearest",
        )

    merged_a = _with_speed(positions_a, telemetry_a)
    merged_b = _with_speed(positions_b, telemetry_b)

    fig = go.Figure()

    if track is not None:
        from f1_coach.presentation.charts.track_registry import get_track_svg_data_uri

        svg_uri = get_track_svg_data_uri(track)
        if svg_uri:
            all_x = pd.concat([merged_a["pos_x"], merged_b["pos_x"]])
            all_z = pd.concat([merged_a["pos_z"], merged_b["pos_z"]])

            min_x, max_x = float(all_x.min()), float(all_x.max())
            min_z, max_z = float(all_z.min()), float(all_z.max())

            center_x = (min_x + max_x) / 2.0
            center_z = (min_z + max_z) / 2.0

            # Tek ortak ölçek: verinin en geniş boyutu + %15 pay, 500px SVG'ye sığdırılır.
            data_extent = max(max_x - min_x, max_z - min_z) * 1.15
            half_extent = max(data_extent, 1.0) / 2.0

            x_left = center_x - half_extent
            z_top = center_z + half_extent  # SVG y ekseni ters olabileceği için üst=büyük z

            fig.add_layout_image(dict(
                source=svg_uri, xref="x", yref="y",
                x=x_left, y=z_top,
                sizex=half_extent * 2, sizey=half_extent * 2,
                xanchor="left", yanchor="top",
                sizing="contain", layer="below", opacity=0.6,
            ))

    fig.add_trace(go.Scatter(
        x=merged_a["pos_x"], y=merged_a["pos_z"],
        mode="lines", name=label_a, line=dict(color=_PURPLE, width=3),
        customdata=merged_a["speed"],
        hovertemplate=f"{label_a}<br>Hız: %{{customdata:.0f}} km/s<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=merged_b["pos_x"], y=merged_b["pos_z"],
        mode="lines", name=label_b, line=dict(color=_COMPARISON_COLOR, width=3),
        customdata=merged_b["speed"],
        hovertemplate=f"{label_b}<br>Hız: %{{customdata:.0f}} km/s<extra></extra>",
    ))

    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=550, showlegend=True,
        margin=dict(l=20, r=20, t=20, b=20),
        template="plotly_dark",
        xaxis_title=None, yaxis_title=None,
        xaxis_showticklabels=False, yaxis_showticklabels=False,
    )
    return _strip_internal_scroll(fig.to_html(include_plotlyjs="cdn", full_html=True))