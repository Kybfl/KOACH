"""CarSetup domain model.

Represents the car's mechanical/aero setup, valid from a specific lap
onward until superseded by another setup (e.g. after a pit stop). F1 25
broadcasts this packet continuously — it is SessionManager's job to turn
that repeating broadcast into discrete "setup changed" rows before they
ever reach this model or a repository.

Kept separate from Lap: a single setup typically spans many laps, so
attaching valid_from_lap here (rather than duplicating setup fields onto
every Lap row) lets the application layer resolve "which setup was fitted
for lap N" on demand.
"""

from dataclasses import dataclass, field


@dataclass
class CarSetup:
    """A car setup, valid from a specific lap onward within a session.

    Attributes:
        session_id:       Foreign key to the parent Session.
        valid_from_lap:   1-based lap number this setup first applied to.
        front_wing / rear_wing:              Aero wing levels.
        on_throttle_diff / off_throttle_diff: Differential adjustment (%).
        front_camber / rear_camber:          Camber angle (radians, signed).
        front_toe / rear_toe:                Toe angle (radians, signed).
        front_suspension / rear_suspension:   Suspension stiffness.
        front_arb / rear_arb:                Anti-roll bar stiffness.
        front_ride_height / rear_ride_height: Ride height.
        brake_pressure:   Brake pressure (%).
        brake_bias:       Brake bias (%, front).
        front_left_tyre_pressure / front_right_tyre_pressure /
        rear_left_tyre_pressure / rear_right_tyre_pressure: Tyre pressure (PSI).
        ballast:          Ballast position.
        fuel_load:        Fuel load (kg) at the moment this setup was
                          captured — informational only, NEVER used to
                          detect setup changes (it decreases continuously
                          as fuel burns, which would falsely register a
                          "new setup" on every lap).
        id:               Database primary key; -1 means not yet persisted.
    """

    session_id: int
    valid_from_lap: int
    front_wing: int
    rear_wing: int
    on_throttle_diff: int
    off_throttle_diff: int
    front_camber: float
    rear_camber: float
    front_toe: float
    rear_toe: float
    front_suspension: int
    rear_suspension: int
    front_arb: int
    rear_arb: int
    front_ride_height: int
    rear_ride_height: int
    brake_pressure: int
    brake_bias: int
    front_left_tyre_pressure: float
    front_right_tyre_pressure: float
    rear_left_tyre_pressure: float
    rear_right_tyre_pressure: float
    ballast: int
    fuel_load: float
    id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1