"""KOACH görsel tema sistemi — Figma tasarımından çıkarılan renk paleti.

Koyu ve açık iki tema desteklenir. Aktif tema, uygulama başlangıcında
set_active_theme() ile belirlenir ve modül seviyesindeki renk sabitleri
o anda güncellenir.

KRİTİK KISIT: set_active_theme() ÇAĞRILMADAN önce hiçbir presentation/
sayfa modülü import edilmemeli. Python'da `from theme import SURFACE`
gibi bir import, değeri o anki haliyle bağlar — sonradan theme.py
içinde değişse bile o modülün gördüğü değer değişmez. Bu yüzden
app.py, tema belirlendikten SONRA MainWindow'u import eder (bkz. app.py).
"""

_PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "BACKGROUND": "#0B0B0D",
        "SURFACE": "#16161A",
        "BORDER": "#26262B",
        "BORDER_INPUT": "#2E2E35",
        "BORDER_HOVER": "#3A3A42",
        "TEXT_PRIMARY": "#F5F5F7",
        "TEXT_SECONDARY": "#9A9AA2",
        "TEXT_MUTED": "#6B6B72",
        "ACCENT_RED": "#E10600",
        "ACCENT_RED_DARK": "#A00400",
        "PURPLE": "#8B5CF6",
        "GREEN": "#22C55E",
        "ORANGE": "#F97316",
        "BLUE": "#38BDF8",
        "YELLOW": "#EAB308",
    },
    "light": {
        "BACKGROUND": "#F5F5F7",
        "SURFACE": "#FFFFFF",
        "BORDER": "#E2E2E6",
        "BORDER_INPUT": "#D0D0D6",
        "BORDER_HOVER": "#B8B8C0",
        "TEXT_PRIMARY": "#0B0B0D",
        "TEXT_SECONDARY": "#6B6B72",
        "TEXT_MUTED": "#9A9AA2",
        "ACCENT_RED": "#E10600",
        "ACCENT_RED_DARK": "#A00400",
        "PURPLE": "#8B5CF6",
        "GREEN": "#16A34A",
        "ORANGE": "#EA580C",
        "BLUE": "#0284C7",
        "YELLOW": "#CA8A04",
    },
}

FONT_FAMILY = "'Inter', 'Segoe UI', sans-serif"

ACTIVE_THEME_NAME = "dark"

# --- Aktif tema renkleri (set_active_theme() ile güncellenir) ---
BACKGROUND = _PALETTES["dark"]["BACKGROUND"]
SURFACE = _PALETTES["dark"]["SURFACE"]
BORDER = _PALETTES["dark"]["BORDER"]
BORDER_INPUT = _PALETTES["dark"]["BORDER_INPUT"]
BORDER_HOVER = _PALETTES["dark"]["BORDER_HOVER"]
TEXT_PRIMARY = _PALETTES["dark"]["TEXT_PRIMARY"]
TEXT_SECONDARY = _PALETTES["dark"]["TEXT_SECONDARY"]
TEXT_MUTED = _PALETTES["dark"]["TEXT_MUTED"]
ACCENT_RED = _PALETTES["dark"]["ACCENT_RED"]
ACCENT_RED_DARK = _PALETTES["dark"]["ACCENT_RED_DARK"]
PURPLE = _PALETTES["dark"]["PURPLE"]
GREEN = _PALETTES["dark"]["GREEN"]
ORANGE = _PALETTES["dark"]["ORANGE"]
BLUE = _PALETTES["dark"]["BLUE"]
YELLOW = _PALETTES["dark"]["YELLOW"]


def set_active_theme(theme_name: str) -> None:
    """Modül seviyesindeki renk sabitlerini seçilen temaya göre günceller.

    ÇAĞRILMA ZAMANI KRİTİK: main_window.py veya herhangi bir sayfa modülü
    import edilmeden önce çağrılmalı. Bkz. modül docstring'i.
    """
    global ACTIVE_THEME_NAME, BACKGROUND, SURFACE, BORDER, BORDER_INPUT, BORDER_HOVER
    global TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED
    global ACCENT_RED, ACCENT_RED_DARK, PURPLE, GREEN, ORANGE, BLUE, YELLOW

    palette = _PALETTES.get(theme_name, _PALETTES["dark"])
    ACTIVE_THEME_NAME = theme_name if theme_name in _PALETTES else "dark"

    BACKGROUND = palette["BACKGROUND"]
    SURFACE = palette["SURFACE"]
    BORDER = palette["BORDER"]
    BORDER_INPUT = palette["BORDER_INPUT"]
    BORDER_HOVER = palette["BORDER_HOVER"]
    TEXT_PRIMARY = palette["TEXT_PRIMARY"]
    TEXT_SECONDARY = palette["TEXT_SECONDARY"]
    TEXT_MUTED = palette["TEXT_MUTED"]
    ACCENT_RED = palette["ACCENT_RED"]
    ACCENT_RED_DARK = palette["ACCENT_RED_DARK"]
    PURPLE = palette["PURPLE"]
    GREEN = palette["GREEN"]
    ORANGE = palette["ORANGE"]
    BLUE = palette["BLUE"]
    YELLOW = palette["YELLOW"]


def rgba(hex_color: str, alpha: float) -> str:
    """'#RRGGBB' + 0.0-1.0 alpha → Qt QSS uyumlu 'rgba(r,g,b,a)' string'i."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def build_global_stylesheet(base_font_size: int = 13) -> str:
    """Uygulama genelinde uygulanacak QSS string'ini üretir.

    Bu fonksiyon çağrıldığı ANDAKİ modül seviyesi renk sabitlerini okur —
    set_active_theme() çağrıldıktan SONRA çağrılması yeterlidir, import
    sırası burada önemli değildir (yalnızca fonksiyon gövdesi, çağrı
    anında güncel globalleri okur).
    """
    return f"""
        QWidget {{
            background-color: {BACKGROUND};
            color: {TEXT_PRIMARY};
            font-family: {FONT_FAMILY};
            font-size: {base_font_size}px;
        }}

        QPushButton {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 8px 16px;
            color: {TEXT_PRIMARY};
        }}
        QPushButton:hover {{
            border-color: {BORDER_HOVER};
        }}
        QPushButton:disabled {{
            color: {TEXT_MUTED};
        }}

        QPushButton#PrimaryButton {{
            background-color: {ACCENT_RED};
            border: none;
            font-weight: 600;
            padding: 10px 20px;
        }}
        QPushButton#PrimaryButton:hover {{
            background-color: {ACCENT_RED_DARK};
        }}

        QLineEdit, QComboBox, QSpinBox, QTextEdit {{
            background-color: {SURFACE};
            border: 1px solid {BORDER_INPUT};
            border-radius: 10px;
            padding: 8px 12px;
            color: {TEXT_PRIMARY};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border-color: {ACCENT_RED};
        }}

        QTableWidget, QListWidget {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 10px;
            gridline-color: {BORDER};
        }}
        QHeaderView::section {{
            background-color: {SURFACE};
            color: {TEXT_SECONDARY};
            border: none;
            padding: 6px;
        }}

        QFrame#TopBar {{
            background-color: {BACKGROUND};
            border-bottom: 1px solid {BORDER};
        }}

        QFrame#Sidebar {{
            background-color: {SURFACE};
            border-right: 1px solid {BORDER};
        }}
    """