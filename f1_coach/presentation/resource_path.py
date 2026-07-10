"""PyInstaller ile paketlenmiş .exe içinde de, kaynaktan çalışırken de
doğru dosya yolunu bulan yardımcı fonksiyon.

PyInstaller --onefile modunda çalışırken tüm dosyalar sys._MEIPASS
altındaki geçici bir klasöre açılır; normal çalışmada bu öznitelik yok.
"""

import sys
from pathlib import Path


def resource_path(relative_to_presentation: str) -> Path:
    """'assets/icons/home-gray.svg' gibi presentation/ köküne göreli bir
    yolu, hem kaynaktan hem .exe içinden çalışırken doğru mutlak yola çevirir.
    """
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "f1_coach" / "presentation"  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent
    return base / relative_to_presentation