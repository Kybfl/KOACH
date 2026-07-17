"""F1 25 UDP packet struct definitions using Python's ctypes.

Only the packets relevant to KOACH are defined here:
    Packet ID 0  — Motion        (excluded by design — not used)
    Packet ID 1  — Session       (track, session type)
    Packet ID 2  — Lap Data      (lap/sector times, validity)
    Packet ID 6  — Car Telemetry (speed, throttle, brake, gear, rpm, drs)
    Packet ID 7  — Car Status    (ers, fuel, tyre compound)

Field names follow the official F1 25 UDP specification document exactly so
that future spec updates are easy to cross-reference.

Reference: EA Sports F1 25 UDP Telemetry Specification
"""

import ctypes


# ---------------------------------------------------------------------------
# Shared header — present at the start of every UDP packet
# ---------------------------------------------------------------------------

class PacketHeader(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_packetFormat",       ctypes.c_uint16),   # 2025
        ("m_gameYear",           ctypes.c_uint8),    # e.g. 25
        ("m_gameMajorVersion",   ctypes.c_uint8),
        ("m_gameMinorVersion",   ctypes.c_uint8),
        ("m_packetVersion",      ctypes.c_uint8),
        ("m_packetId",           ctypes.c_uint8),    # which packet type
        ("m_sessionUID",         ctypes.c_uint64),   # unique session identifier
        ("m_sessionTime",        ctypes.c_float),    # seconds since session start
        ("m_frameIdentifier",    ctypes.c_uint32),
        ("m_overallFrameIdentifier", ctypes.c_uint32),
        ("m_playerCarIndex",     ctypes.c_uint8),    # index of player car (0–21)
        ("m_secondaryPlayerCarIndex", ctypes.c_uint8),
    ]

# ---------------------------------------------------------------------------
# Packet ID 0 — Motion Data
# ---------------------------------------------------------------------------

class CarMotionData(ctypes.LittleEndianStructure):
    """Per-car motion entry (one of 22 in the packet)."""
    _pack_ = 1
    _fields_ = [
        ("m_worldPositionX",     ctypes.c_float),
        ("m_worldPositionY",     ctypes.c_float),
        ("m_worldPositionZ",     ctypes.c_float),
        ("m_worldVelocityX",     ctypes.c_float),
        ("m_worldVelocityY",     ctypes.c_float),
        ("m_worldVelocityZ",     ctypes.c_float),
        ("m_worldForwardDirX",   ctypes.c_int16),
        ("m_worldForwardDirY",   ctypes.c_int16),
        ("m_worldForwardDirZ",   ctypes.c_int16),
        ("m_worldRightDirX",     ctypes.c_int16),
        ("m_worldRightDirY",     ctypes.c_int16),
        ("m_worldRightDirZ",     ctypes.c_int16),
        ("m_gForceLateral",      ctypes.c_float),
        ("m_gForceLongitudinal", ctypes.c_float),
        ("m_gForceVertical",     ctypes.c_float),
        ("m_yaw",                ctypes.c_float),
        ("m_pitch",              ctypes.c_float),
        ("m_roll",               ctypes.c_float),
    ]


class PacketMotionData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header",        PacketHeader),
        ("m_carMotionData", CarMotionData * 22),
    ]

# ---------------------------------------------------------------------------
# Packet ID 1 — Session Data
# ---------------------------------------------------------------------------

class MarshalZone(ctypes.LittleEndianStructure):
    """One marshal zone entry within PacketSessionData."""
    _pack_ = 1
    _fields_ = [
        ("m_zoneStart", ctypes.c_float),   # fraction (0..1) of lap where zone starts
        ("m_zoneFlag",  ctypes.c_int8),    # -1=unknown, 0=none, 1=green, 2=blue, 3=yellow
    ]


class WeatherForecastSample(ctypes.LittleEndianStructure):
    """One weather forecast sample entry within PacketSessionData."""
    _pack_ = 1
    _fields_ = [
        ("m_sessionType",            ctypes.c_uint8),
        ("m_timeOffset",             ctypes.c_uint8),
        ("m_weather",                ctypes.c_uint8),
        ("m_trackTemperature",       ctypes.c_int8),
        ("m_trackTemperatureChange", ctypes.c_int8),
        ("m_airTemperature",         ctypes.c_int8),
        ("m_airTemperatureChange",   ctypes.c_int8),
        ("m_rainPercentage",         ctypes.c_uint8),
    ]


class PacketSessionData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header",                  PacketHeader),
        ("m_weather",                 ctypes.c_uint8),
        ("m_trackTemperature",        ctypes.c_int8),
        ("m_airTemperature",          ctypes.c_int8),
        ("m_totalLaps",               ctypes.c_uint8),
        ("m_trackLength",             ctypes.c_uint16),
        ("m_sessionType",             ctypes.c_uint8),   # → SessionType enum
        ("m_trackId",                 ctypes.c_int8),    # → TrackName enum (-1 = unknown)
        ("m_formula",                 ctypes.c_uint8),
        ("m_sessionTimeLeft",         ctypes.c_uint16),
        ("m_sessionDuration",         ctypes.c_uint16),
        ("m_pitSpeedLimit",           ctypes.c_uint8),
        ("m_gamePaused",              ctypes.c_uint8),
        ("m_isSpectating",            ctypes.c_uint8),
        ("m_spectatorCarIndex",       ctypes.c_uint8),
        ("m_sliProNativeSupport",     ctypes.c_uint8),
        ("m_numMarshalZones",         ctypes.c_uint8),
        ("m_marshalZones",            MarshalZone * 21),
        ("m_safetyCarStatus",         ctypes.c_uint8),
        ("m_networkGame",             ctypes.c_uint8),
        ("m_numWeatherForecastSamples", ctypes.c_uint8),
        ("m_weatherForecastSamples",  WeatherForecastSample * 64),
        ("m_forecastAccuracy",        ctypes.c_uint8),
        ("m_aiDifficulty",            ctypes.c_uint8),
        ("m_seasonLinkIdentifier",    ctypes.c_uint32),
        ("m_weekendLinkIdentifier",   ctypes.c_uint32),
        ("m_sessionLinkIdentifier",   ctypes.c_uint32),
        ("m_pitStopWindowIdealLap",   ctypes.c_uint8),
        ("m_pitStopWindowLatestLap",  ctypes.c_uint8),
        ("m_pitStopRejoinPosition",   ctypes.c_uint8),
        ("m_steeringAssist",          ctypes.c_uint8),
        ("m_brakingAssist",           ctypes.c_uint8),
        ("m_gearboxAssist",           ctypes.c_uint8),
        ("m_pitAssist",               ctypes.c_uint8),
        ("m_pitReleaseAssist",        ctypes.c_uint8),
        ("m_ERSAssist",               ctypes.c_uint8),
        ("m_DRSAssist",               ctypes.c_uint8),
        ("m_dynamicRacingLine",       ctypes.c_uint8),
        ("m_dynamicRacingLineType",   ctypes.c_uint8),
        ("m_gameMode",                ctypes.c_uint8),
        ("m_ruleSet",                 ctypes.c_uint8),
        ("m_timeOfDay",               ctypes.c_uint32),
        ("m_sessionLength",           ctypes.c_uint8),
        ("m_speedUnitsLeadPlayer",    ctypes.c_uint8),
        ("m_temperatureUnitsLeadPlayer", ctypes.c_uint8),
        ("m_speedUnitsSecondaryPlayer", ctypes.c_uint8),
        ("m_temperatureUnitsSecondaryPlayer", ctypes.c_uint8),
        ("m_numSafetyCarPeriods",     ctypes.c_uint8),
        ("m_numVirtualSafetyCarPeriods", ctypes.c_uint8),
        ("m_numRedFlagPeriods",       ctypes.c_uint8),
        ("m_equalCarPerformance",     ctypes.c_uint8),
        ("m_recoveryMode",            ctypes.c_uint8),
        ("m_flashbackLimit",          ctypes.c_uint8),
        ("m_surfaceType",             ctypes.c_uint8),
        ("m_lowFuelMode",             ctypes.c_uint8),
        ("m_raceStarts",              ctypes.c_uint8),
        ("m_tyreTemperature",         ctypes.c_uint8),
        ("m_pitLaneTyreSim",          ctypes.c_uint8),
        ("m_carDamage",               ctypes.c_uint8),
        ("m_carDamageRate",           ctypes.c_uint8),
        ("m_collisions",              ctypes.c_uint8),
        ("m_collisionsOffForFirstLapOnly", ctypes.c_uint8),
        ("m_mpUnsafePitRelease",      ctypes.c_uint8),
        ("m_mpOffForGriefing",        ctypes.c_uint8),
        ("m_cornerCuttingStringency", ctypes.c_uint8),
        ("m_parcFermeRules",          ctypes.c_uint8),
        ("m_pitStopExperience",       ctypes.c_uint8),
        ("m_safetyCar",               ctypes.c_uint8),
        ("m_safetyCarExperience",     ctypes.c_uint8),
        ("m_formationLap",            ctypes.c_uint8),
        ("m_formationLapExperience",  ctypes.c_uint8),
        ("m_redFlags",                ctypes.c_uint8),
        ("m_affectsLicenceLevelSolo", ctypes.c_uint8),
        ("m_affectsLicenceLevelMP",   ctypes.c_uint8),
        ("m_numSessionsInWeekend",    ctypes.c_uint8),
        ("m_weekendStructure",        ctypes.c_uint8 * 12),
        ("m_sector2LapDistanceStart", ctypes.c_float),
        ("m_sector3LapDistanceStart", ctypes.c_float),
    ]


# ---------------------------------------------------------------------------
# Packet ID 2 — Lap Data
# ---------------------------------------------------------------------------

class LapData(ctypes.LittleEndianStructure):
    """Per-car lap data entry (one of 22 in the packet)."""
    _pack_ = 1
    _fields_ = [
        ("m_lastLapTimeInMS",             ctypes.c_uint32),
        ("m_currentLapTimeInMS",          ctypes.c_uint32),
        ("m_sector1TimeInMS",             ctypes.c_uint16),
        ("m_sector1TimeMinutes",          ctypes.c_uint8),
        ("m_sector2TimeInMS",             ctypes.c_uint16),
        ("m_sector2TimeMinutes",          ctypes.c_uint8),
        ("m_deltaToCarInFrontInMS",       ctypes.c_uint16),
        ("m_deltaToCarInFrontMinutes",    ctypes.c_uint8),
        ("m_deltaToRaceLeaderInMS",       ctypes.c_uint16),
        ("m_deltaToRaceLeaderMinutes",    ctypes.c_uint8),
        ("m_lapDistance",                 ctypes.c_float),
        ("m_totalDistance",               ctypes.c_float),
        ("m_safetyCarDelta",              ctypes.c_float),
        ("m_carPosition",                 ctypes.c_uint8),
        ("m_currentLapNum",               ctypes.c_uint8),
        ("m_pitStatus",                   ctypes.c_uint8),
        ("m_numPitStops",                 ctypes.c_uint8),
        ("m_sector",                      ctypes.c_uint8),   # 0=S1, 1=S2, 2=S3
        ("m_currentLapInvalid",           ctypes.c_uint8),   # 1 = invalid
        ("m_penalties",                   ctypes.c_uint8),
        ("m_totalWarnings",               ctypes.c_uint8),
        ("m_cornerCuttingWarnings",       ctypes.c_uint8),
        ("m_numUnservedDriveThroughPens", ctypes.c_uint8),
        ("m_numUnservedStopGoPens",       ctypes.c_uint8),
        ("m_gridPosition",                ctypes.c_uint8),
        ("m_driverStatus",                ctypes.c_uint8),
        ("m_resultStatus",                ctypes.c_uint8),
        ("m_pitLaneTimerActive",          ctypes.c_uint8),
        ("m_pitLaneTimeInLaneInMS",       ctypes.c_uint16),
        ("m_pitStopTimerInMS",            ctypes.c_uint16),
        ("m_pitStopShouldServePen",       ctypes.c_uint8),
        ("m_speedTrapFastestSpeed",       ctypes.c_float),
        ("m_speedTrapFastestLap",         ctypes.c_uint8),
    ]


class PacketLapData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header",       PacketHeader),
        ("m_lapData",      LapData * 22),
        ("m_timeTrialPBCarIdx",   ctypes.c_uint8),
        ("m_timeTrialRivalCarIdx", ctypes.c_uint8),
    ]


# ---------------------------------------------------------------------------
# Packet ID 6 — Car Telemetry
# ---------------------------------------------------------------------------

class CarTelemetryData(ctypes.LittleEndianStructure):
    """Per-car telemetry entry (one of 22 in the packet)."""
    _pack_ = 1
    _fields_ = [
        ("m_speed",                   ctypes.c_uint16),
        ("m_throttle",                ctypes.c_float),
        ("m_steer",                   ctypes.c_float),
        ("m_brake",                   ctypes.c_float),
        ("m_clutch",                  ctypes.c_uint8),
        ("m_gear",                    ctypes.c_int8),
        ("m_engineRPM",               ctypes.c_uint16),
        ("m_drs",                     ctypes.c_uint8),   # 0=off, 1=on
        ("m_revLightsPercent",        ctypes.c_uint8),
        ("m_revLightsBitValue",       ctypes.c_uint16),
        ("m_brakesTemperature",       ctypes.c_uint16 * 4),
        ("m_tyresSurfaceTemperature", ctypes.c_uint8 * 4),
        ("m_tyresInnerTemperature",   ctypes.c_uint8 * 4),
        ("m_engineTemperature",       ctypes.c_uint16),
        ("m_tyresPressure",           ctypes.c_float * 4),
        ("m_surfaceType",             ctypes.c_uint8 * 4),
    ]


class PacketCarTelemetryData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header",          PacketHeader),
        ("m_carTelemetryData", CarTelemetryData * 22),
        ("m_mfdPanelIndex",   ctypes.c_uint8),
        ("m_mfdPanelIndexSecondaryPlayer", ctypes.c_uint8),
        ("m_suggestedGear",   ctypes.c_int8),
    ]


# ---------------------------------------------------------------------------
# Packet ID 7 — Car Status
# ---------------------------------------------------------------------------

class CarStatusData(ctypes.LittleEndianStructure):
    """Per-car status entry (one of 22 in the packet)."""
    _pack_ = 1
    _fields_ = [
        ("m_tractionControl",         ctypes.c_uint8),
        ("m_antiLockBrakes",          ctypes.c_uint8),
        ("m_fuelMix",                 ctypes.c_uint8),
        ("m_frontBrakeBias",          ctypes.c_uint8),
        ("m_pitLimiterStatus",        ctypes.c_uint8),
        ("m_fuelInTank",              ctypes.c_float),
        ("m_fuelCapacity",            ctypes.c_float),
        ("m_fuelRemainingLaps",       ctypes.c_float),
        ("m_maxRPM",                  ctypes.c_uint16),
        ("m_idleRPM",                 ctypes.c_uint16),
        ("m_maxGears",                ctypes.c_uint8),
        ("m_drsAllowed",              ctypes.c_uint8),
        ("m_drsActivationDistance",   ctypes.c_uint16),
        ("m_actualTyreCompound",      ctypes.c_uint8),
        ("m_visualTyreCompound",      ctypes.c_uint8),
        ("m_tyresAgeLaps",            ctypes.c_uint8),
        ("m_vehicleFiaFlags",         ctypes.c_int8),
        ("m_enginePowerICE",          ctypes.c_float),
        ("m_enginePowerMGUK",         ctypes.c_float),
        ("m_ersStoreEnergy",          ctypes.c_float),   # Joules
        ("m_ersDeployMode",           ctypes.c_uint8),
        ("m_ersHarvestedThisLapMGUK", ctypes.c_float),
        ("m_ersHarvestedThisLapMGUH", ctypes.c_float),
        ("m_ersDeployedThisLap",      ctypes.c_float),
        ("m_networkPaused",           ctypes.c_uint8),
    ]


class PacketCarStatusData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header",        PacketHeader),
        ("m_carStatusData", CarStatusData * 22),
    ]

# ---------------------------------------------------------------------------
# Packet ID 5 — Car Setups
# ---------------------------------------------------------------------------

class CarSetupData(ctypes.LittleEndianStructure):
    """Per-car setup entry (one of 22 in the packet)."""
    _pack_ = 1
    _fields_ = [
        ("m_frontWing",              ctypes.c_uint8),
        ("m_rearWing",               ctypes.c_uint8),
        ("m_onThrottle",             ctypes.c_uint8),
        ("m_offThrottle",            ctypes.c_uint8),
        ("m_frontCamber",            ctypes.c_float),
        ("m_rearCamber",             ctypes.c_float),
        ("m_frontToe",               ctypes.c_float),
        ("m_rearToe",                ctypes.c_float),
        ("m_frontSuspension",        ctypes.c_uint8),
        ("m_rearSuspension",         ctypes.c_uint8),
        ("m_frontAntiRollBar",       ctypes.c_uint8),
        ("m_rearAntiRollBar",        ctypes.c_uint8),
        ("m_frontSuspensionHeight",  ctypes.c_uint8),
        ("m_rearSuspensionHeight",   ctypes.c_uint8),
        ("m_brakePressure",          ctypes.c_uint8),
        ("m_brakeBias",              ctypes.c_uint8),
        ("m_engineBraking",          ctypes.c_uint8),
        ("m_rearLeftTyrePressure",   ctypes.c_float),
        ("m_rearRightTyrePressure",  ctypes.c_float),
        ("m_frontLeftTyrePressure",  ctypes.c_float),
        ("m_frontRightTyrePressure", ctypes.c_float),
        ("m_ballast",                ctypes.c_uint8),
        ("m_fuelLoad",               ctypes.c_float),
    ]


class PacketCarSetupData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header",             PacketHeader),
        ("m_carSetupData",       CarSetupData * 22),
        ("m_nextFrontWingValue", ctypes.c_float),
    ]

# ---------------------------------------------------------------------------
# Packet ID lookup
# ---------------------------------------------------------------------------

PACKET_ID_TO_STRUCT: dict[int, type] = {
    0: PacketMotionData,
    1: PacketSessionData,
    2: PacketLapData,
    5: PacketCarSetupData,   
    6: PacketCarTelemetryData,
    7: PacketCarStatusData,
}

HEADER_SIZE = ctypes.sizeof(PacketHeader)
