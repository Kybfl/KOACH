"""Pist SVG dosyalarının TrackName'e eşlenmesi ve manuel kalibrasyon verileri.

Her pist için world_x0/z0/x1/z1, SVG'nin (0,0) ve (500,500) piksel
köşelerinin UDP world koordinat sistemindeki (metre) karşılıklarını tanımlar.
Bu değerler otomatik hesaplanamaz — ilk render'dan sonra racing line ile
pist şeklinin üst üste gelip gelmediğine bakılıp gözle ayarlanır.
"""

import base64
from dataclasses import dataclass

from f1_coach.domain.models.f125.enums import TrackName
from f1_coach.presentation.resource_path import resource_path


@dataclass(frozen=True)
class TrackCalibration:
    """SVG piksel uzayını (0,0)-(500,500) world metre uzayına eşleyen kalibrasyon."""

    world_x0: float   # SVG (0,0) köşesinin karşılığı — world X
    world_z0: float   # SVG (0,0) köşesinin karşılığı — world Z
    world_x1: float   # SVG (500,500) köşesinin karşılığı — world X
    world_z1: float   # SVG (500,500) köşesinin karşılığı — world Z


# Dosya adları — assets/tracks/ klasörüne konan SVG dosyalarıyla eşleşmeli.
# Yeni pist eklendikçe bu sözlüğe yeni satır eklenir.
TRACK_SVG_FILES: dict[TrackName, str] = {
    TrackName.MELBOURNE: "melbourne.svg",
    TrackName.SHANGHAI: "shanghai.svg",
    TrackName.BAHRAIN: "bahrain.svg",
    TrackName.BARCELONA: "barcelona.svg",
    TrackName.MONACO: "monaco.svg",
    TrackName.MONTREAL: "montreal.svg",
    TrackName.SILVERSTONE: "silverstone.svg",
    TrackName.BUDAPEST: "budapest.svg",
    TrackName.SPA: "spa.svg",
    TrackName.MONZA: "monza.svg",
    TrackName.SINGAPORE: "singapore.svg",
    TrackName.SUZUKA: "suzuka.svg",
    TrackName.ABU_DHABI: "abu_dhabi.svg",
    TrackName.AUSTIN: "austin.svg",
    TrackName.SAO_PAULO: "sao_paulo.svg",
    TrackName.AUSTRIA: "austria.svg",
    TrackName.MEXICO_CITY: "mexico_city.svg",
    TrackName.BAKU: "baku.svg",
    TrackName.ZANDVOORT: "zandvoort.svg",
    TrackName.IMOLA: "imola.svg",
    TrackName.JEDDAH: "jeddah.svg",
    TrackName.MIAMI: "miami.svg",
    TrackName.LAS_VEGAS: "las_vegas.svg",
    TrackName.LUSAIL: "lusail.svg",
}



def get_track_svg_data_uri(track: TrackName) -> str | None:
    """Pist için SVG dosyasını, çizgileri inceltilmiş ve ters çevrilmiş halde base64 data URI olarak döner.

    Orijinal SVG'ler kalın çizilmiş (stroke-width 20/5) — racing line'ların
    üzerinde net görünmesi için burada inceltiyoruz, kaynak dosyaya dokunmuyoruz.
    Ayrıca pisti doğru hizalamak için X ekseninde ters çeviriyoruz.
    """
    filename = TRACK_SVG_FILES.get(track)
    if filename is None:
        return None

    svg_path = resource_path("assets/tracks") / filename
    if not svg_path.exists():
        return None

    # Dosyayı metin olarak oku
    svg_text = svg_path.read_text(encoding="utf-8")
    
    # Çizgileri incelt
    svg_text = svg_text.replace("stroke-width:20", "stroke-width:6")
    svg_text = svg_text.replace("stroke-width:5", "stroke-width:2")

    # X eksenine göre (sağ-sol) ters çevir
    if "<svg" in svg_text:
        svg_text = svg_text.replace("<svg", "<svg style=\"transform: scale(1, -1);\"", 1)

    # Base64 olarak kodla
    encoded = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
