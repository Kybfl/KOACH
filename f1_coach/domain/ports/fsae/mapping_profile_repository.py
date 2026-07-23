"""MappingProfileRepository port.

Bilerek yalnızca CRUD sağlıyor — "profili session'a uygula" gibi iş
mantığı burada değil, application/fsae/mapping_profile_applier.py'de
(saf fonksiyon) ve presentation katmanında (orkestrasyon) yaşıyor.
"""

from typing import Protocol

from f1_coach.domain.models.fsae.mapping_profile import MappingProfile, MappingProfileEntry


class MappingProfileRepository(Protocol):
    """Persistence contract for MappingProfile + its entries."""

    def save_profile(self, profile: MappingProfile) -> None:
        """Insert or update a profile row (yalnızca isim/tarih — entries ayrı).

        Sets ``profile.id`` after a successful insert.
        """
        ...

    def get_all_profiles(self) -> list[MappingProfile]:
        """Return all profiles, alphabetically by name."""
        ...

    def delete_profile(self, profile_id: int) -> None:
        """Remove a profile and cascade to its entries."""
        ...

    def replace_entries(self, profile_id: int, entries: list[MappingProfileEntry]) -> None:
        """Bir profilin TÜM entry'lerini verilen listeyle değiştirir.

        Hem yeni profil oluştururken hem mevcut bir profili güncel
        session'ın mapping'leriyle güncellerken kullanılır — kısmi
        ekleme/çıkarma yok, her zaman tam değiştirme.
        """
        ...

    def get_entries(self, profile_id: int) -> list[MappingProfileEntry]:
        """Return all entries for a profile."""
        ...