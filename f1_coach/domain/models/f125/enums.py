"""Domain enumerations for KOACH.

These enums map directly to the integer values broadcast by F1 25 UDP packets.
The mapping is performed in the infrastructure layer (TelemetryMapper); the
domain itself only ever works with these symbolic names.
"""

from enum import Enum


class WeatherCondition(Enum):
    """F1 25 UDP weather identifiers (Packet ID 1, m_weather field).

    Sampled per-lap (not per-session) because weather can change mid-session
    — a single session-level field would misrepresent laps driven after a
    weather transition (e.g. rain starting mid-race).
    """

    CLEAR = 0
    LIGHT_CLOUD = 1
    OVERCAST = 2
    LIGHT_RAIN = 3
    HEAVY_RAIN = 4
    STORM = 5

    @property
    def is_wet(self) -> bool:
        """True for any condition where tyre/braking behaviour differs from dry."""
        return self in (WeatherCondition.LIGHT_RAIN, WeatherCondition.HEAVY_RAIN, WeatherCondition.STORM)

    @property
    def display_name(self) -> str:
        _labels: dict[int, str] = {
            0: "Açık",
            1: "Parçalı Bulutlu",
            2: "Kapalı",
            3: "Hafif Yağmur",
            4: "Sağanak Yağmur",
            5: "Fırtına",
        }
        return _labels.get(self.value, "Bilinmiyor")

    @classmethod
    def from_udp(cls, value: int) -> "WeatherCondition":
        """Safely construct from a raw UDP integer; falls back to CLEAR."""
        try:
            return cls(value)
        except ValueError:
            return cls.CLEAR


class SessionType(Enum):
    """F1 25 UDP session type identifiers (Packet ID 1, m_sessionType field).

    Values verified against the official F1 25 UDP specification (2026-07).
    Sprint Shootout (10-14) all consolidate into SPRINT; Race 2/3 (16-17)
    consolidate into RACE — KOACH treats these as functionally identical
    to their base session type.
    """

    UNKNOWN = 0
    PRACTICE_1 = 1
    PRACTICE_2 = 2
    PRACTICE_3 = 3
    SHORT_PRACTICE = 4
    QUALIFYING_1 = 5
    QUALIFYING_2 = 6
    QUALIFYING_3 = 7
    SHORT_QUALIFYING = 8
    OSQ = 9          # One-shot qualifying
    SPRINT = 10
    RACE = 15
    TIME_TRIAL = 18

    @property
    def display_name(self) -> str:
        """Human-readable Turkish label for the UI."""
        _labels: dict[int, str] = {
            0: "Bilinmiyor",
            1: "Antrenman 1",
            2: "Antrenman 2",
            3: "Antrenman 3",
            4: "Kısa Antrenman",
            5: "Sıralama 1",
            6: "Sıralama 2",
            7: "Sıralama 3",
            8: "Kısa Sıralama",
            9: "Tek Tur Sıralama",
            10: "Sprint Sıralama",
            15: "Yarış",
            18: "Zaman Deneme",
        }
        return _labels.get(self.value, "Bilinmiyor")

    @classmethod
    def from_udp(cls, value: int) -> "SessionType":
        """Safely construct from a raw UDP integer; falls back to UNKNOWN."""
        if value in (11, 12, 13, 14):   # Sprint Shootout 2/3/Short/OneShot → SPRINT
            return cls.SPRINT
        if value in (16, 17):           # Race 2 / Race 3 → RACE
            return cls.RACE
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


class TrackName(Enum):
    """F1 25 track identifiers (Packet ID 1, m_trackId field).

    Values verified against the official F1 25 UDP specification (2026-07).
    Track IDs are NOT sequential — they carry historical numbering baggage
    from retired tracks/layouts in earlier F1 games (hence the gaps).
    UNKNOWN (-1) is used when the packet reports an unrecognised track id.
    """

    UNKNOWN = -1
    MELBOURNE = 0 #
    SHANGHAI = 2 #
    BAHRAIN = 3 #
    BARCELONA = 4 #
    MONACO = 5 #
    MONTREAL = 6 #
    SILVERSTONE = 7 #
    BUDAPEST = 9 #
    SPA = 10 #
    MONZA = 11 #
    SINGAPORE = 12 #
    SUZUKA = 13 #
    ABU_DHABI = 14 #
    AUSTIN = 15 #
    SAO_PAULO = 16 #
    AUSTRIA = 17 #
    MEXICO_CITY = 19 #
    BAKU = 20 #
    ZANDVOORT = 26 #
    IMOLA = 27
    JEDDAH = 29 #
    MIAMI = 30 #
    LAS_VEGAS = 31 #
    LUSAIL = 32 #
    SILVERSTONE_REVERSE = 39 #
    AUSTRIA_REVERSE = 40 #
    ZANDVOORT_REVERSE = 41 #

    @property
    def display_name(self) -> str:
        """Human-readable track name for the UI."""
        _labels: dict[int, str] = {
            -1: "Bilinmiyor",
            0: "Melbourne",
            2: "Şanghay",
            3: "Bahreyn",
            4: "Barselona",
            5: "Monako",
            6: "Montreal",
            7: "Silverstone",
            9: "Budapeşte",
            10: "Spa",
            11: "Monza",
            12: "Singapur",
            13: "Suzuka",
            14: "Abu Dabi",
            15: "Austin",
            16: "Sao Paulo",
            17: "Avusturya",
            19: "Meksika City",
            20: "Bakü",
            26: "Zandvoort",
            27: "Imola",
            29: "Cidde",
            30: "Miami",
            31: "Las Vegas",
            32: "Lusail",
            39: "Silverstone (Ters)",
            40: "Avusturya (Ters)",
            41: "Zandvoort (Ters)",
        }
        return _labels.get(self.value, "Bilinmiyor")

    @classmethod
    def from_udp(cls, value: int) -> "TrackName":
        """Safely construct from a raw UDP integer; falls back to UNKNOWN."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN
