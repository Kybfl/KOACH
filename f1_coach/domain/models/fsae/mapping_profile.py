"""MappingProfile / MappingProfileEntry domain modelleri.

Bir araç/konfigürasyon için tekrar kullanılabilir CAN etiketleme şablonu.
ChannelMapping'den farkı: session_id yerine profile_id taşır — bir profil
birden fazla session'a "başlangıç noktası" olarak uygulanabilir (bkz.
application/fsae/mapping_profile_applier.py), ama uygulandığında ürettiği
satırlar normal, session-scoped ChannelMapping satırlarına dönüşür — yani
profil sadece bir şablon, session'ın kendi mapping'lerinin yerini almaz.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MappingProfile:
    """Bir araç/konfigürasyon için isimli etiketleme şablonu.

    Attributes:
        name:       Kullanıcının verdiği isim (ör. "Araç A 2026").
        created_at: Profilin ilk oluşturulduğu zaman.
        id:         Veritabanı birincil anahtarı; -1 henüz kaydedilmedi demek.
    """

    name: str
    created_at: datetime = field(default_factory=datetime.now)
    id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1


@dataclass
class MappingProfileEntry:
    """Bir profildeki tek bir sinyal tanımı — ChannelMapping ile aynı alanlar,
    session_id yerine profile_id taşır.

    Attributes:
        profile_id: Bağlı olduğu MappingProfile.
        (geri kalan alanlar ChannelMapping ile birebir aynı anlamda.)
        id:         Veritabanı birincil anahtarı; -1 henüz kaydedilmedi demek.
    """

    profile_id: int
    can_id: int
    start_byte: int
    bit_length: int
    little_endian: bool
    signed: bool
    scale: float
    offset: float
    name: str
    unit: str
    id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1