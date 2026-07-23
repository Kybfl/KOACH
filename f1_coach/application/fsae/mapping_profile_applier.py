"""mapping_profile_applier — bir MappingProfile'ın entry'lerini, mevcut
session'ın ChannelMapping'leriyle birleştirir.

Session'da zaten (can_id, start_byte) eşleşmesiyle elle girilmiş bir kanal
ASLA ezilmez — profil yalnızca BOŞLUKLARI dolduruyor. Bu sayede aynı araç/
konfigürasyondan gelen yeni bir session çoğunlukla kendini otomatik
etiketlerken, o session'da yapılmış elle düzeltmeler de korunuyor.
"""

from f1_coach.domain.models.fsae.channel_mapping import ChannelMapping
from f1_coach.domain.models.fsae.mapping_profile import MappingProfileEntry


def apply_profile_entries(
    session_id: int,
    existing_mappings: list[ChannelMapping],
    profile_entries: list[MappingProfileEntry],
    available_can_ids: set[int],
) -> list[ChannelMapping]:
    """Profilden, bu session'a eklenebilecek yeni ChannelMapping'leri üretir.

    Args:
        session_id:         Yeni mapping'lerin ait olacağı session.
        existing_mappings:  Session'da zaten tanımlı mapping'ler — asla ezilmez.
        profile_entries:    Seçilen profildeki entry'ler.
        available_can_ids:  Bu session'ın ham log'unda gerçekten bulunan
                            CAN ID'leri — log'da olmayan bir ID için profil
                            entry'si varsa, decode edilecek veri olmadığı
                            için atlanır.

    Returns:
        Henüz kaydedilmemiş (id=-1) yeni ChannelMapping nesneleri. Kalıcı
        hale getirmek ve tabloyu güncellemek çağıranın sorumluluğunda.
    """
    covered = {(m.can_id, m.start_byte) for m in existing_mappings}

    new_mappings: list[ChannelMapping] = []
    for entry in profile_entries:
        if entry.can_id not in available_can_ids:
            continue
        key = (entry.can_id, entry.start_byte)
        if key in covered:
            continue
        new_mappings.append(
            ChannelMapping(
                session_id=session_id,
                can_id=entry.can_id,
                start_byte=entry.start_byte,
                bit_length=entry.bit_length,
                little_endian=entry.little_endian,
                signed=entry.signed,
                scale=entry.scale,
                offset=entry.offset,
                name=entry.name,
                unit=entry.unit,
            )
        )
        covered.add(key)

    return new_mappings