"""Session domain model.

A Session groups all laps driven in one continuous stint — a practice session,
qualifying run, or race. The session_uid comes from the UDP header (m_sessionUID)
and is used as the stable external identifier across restarts.

Assist settings are session-level (not per-lap) because they are a player
configuration that does not change mid-session, unlike weather or safety car
status which are tracked on Lap instead.
"""

from dataclasses import dataclass, field
from datetime import datetime

from f1_coach.domain.models.f125.enums import SessionType, TrackName, WeatherCondition
from f1_coach.domain.models.f125.lap import Lap


@dataclass
class Session:
    """One F1 25 game session.

    Attributes:
        session_uid:               The 64-bit UID broadcast in every UDP packet
                                   header (m_sessionUID), stored as a hex string.
        track:                     Track enum value resolved from UDP m_trackId.
        session_type:              Session type resolved from UDP m_sessionType.
        created_at:                Wall-clock datetime when the session was first
                                   detected.
        steering_assist:           True if steering assist was enabled.
        braking_assist:            0=off, 1=low, 2=medium, 3=high.
        gearbox_assist:            1=manual, 2=manual+suggested, 3=auto.
        ers_assist:                True if ERS assist was enabled.
        drs_assist:                True if DRS assist was enabled.
        dynamic_racing_line:       0=off, 1=corners only, 2=full.
        corner_cutting_stringency: 0=regular, 1=strict — context for AI prompt,
                                   explains how strictly is_valid was enforced.
        laps:                      Ordered list of Lap objects; appended as each
                                   lap completes.
        id:                        Database primary key; -1 means not yet persisted.
    """

    session_uid: str
    track: TrackName
    session_type: SessionType
    created_at: datetime = field(default_factory=datetime.now)
    steering_assist: bool = field(default=False)
    braking_assist: int = field(default=0)
    gearbox_assist: int = field(default=3)
    ers_assist: bool = field(default=False)
    drs_assist: bool = field(default=False)
    dynamic_racing_line: int = field(default=0)
    corner_cutting_stringency: int = field(default=0)
    laps: list[Lap] = field(default_factory=list)
    id: int = field(default=-1)

    # ------------------------------------------------------------------
    # Derived properties used by the application layer and UI
    # ------------------------------------------------------------------

    @property
    def best_lap(self) -> Lap | None:
        """Fastest lap eligible as a reference in this session, or None.

        A lap must be both track-limit valid AND free of safety car influence
        to qualify — see Lap.is_valid_reference. Note: is_valid alone gates
        only reference/best-lap selection, never AI analysis eligibility —
        an invalidated lap can still carry useful telemetry for coaching.
        """
        eligible = [lap for lap in self.laps if lap.is_valid_reference]
        if not eligible:
            return None
        return min(eligible, key=lambda lap: lap.lap_time)

    @property
    def lap_count(self) -> int:
        """Total number of laps (valid + invalid)."""
        return len(self.laps)

    @property
    def dominant_weather(self) -> WeatherCondition | None:
        """Session'daki en sık görülen hava durumu, veya hiç tur yoksa None.

        Yalnızca gösterim/filtreleme amaçlıdır — hava durumu gerçekte Lap
        seviyesinde tutulur (bir session içinde değişebilir), bu property
        yalnızca kart/liste görünümlerinde tek bir özet değer sunar.
        """
        if not self.laps:
            return None
        from collections import Counter

        counts = Counter(lap.weather for lap in self.laps)
        return counts.most_common(1)[0][0]

    @property
    def is_persisted(self) -> bool:
        """True when this session has been saved to the database."""
        return self.id != -1

    def add_lap(self, lap: Lap) -> None:
        """Append a completed lap and set its session reference."""
        lap.session_id = self.id
        self.laps.append(lap)