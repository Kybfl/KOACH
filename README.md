# KOACH

<img width="200" alt="koach_siyah" src="https://github.com/user-attachments/assets/fe0823af-b6aa-43ad-9f8a-8d722ef38ba6" />

**F1 25 telemetry analysis, Formula Student vehicle telemetry, and AI-powered post-session coaching — a native desktop app.**

KOACH started as an F1 25 UDP telemetry coach and has grown into a two-module desktop application: real-time F1 25 telemetry capture with AI coaching, and offline Formula Student (FSAE) CAN log analysis with manual channel labeling. Both modules share the same local-first storage philosophy (SQLite + Parquet) and hexagonal architecture — entirely passive on the F1 25 side (zero interference with the game), entirely offline on the FSAE side (no cloud, no telemetry radio required).

---

## Modules

### F1 25
- **Real-time UDP telemetry capture** — listens on port 20777 (configurable), parses official F1 25 packet structures via `ctypes`
- **Interactive lap analysis** — Plotly-powered speed, throttle/brake overlay, and gear charts, aligned by track position (0.0–1.0) for accurate lap comparison
- **Track map overlay** — two laps' racing lines plotted over the circuit outline, speed-colored on hover
- **Car setup tracking** — detects and logs setup changes across pit stops within a session, with AI-generated trade-off analysis
- **AI coaching feedback** — sector-based, statistically-grounded post-lap analysis via Groq, Anthropic, or Gemini (your choice, your API key)
- **Reference lap hierarchy** — compares against session-best, then track-best, filtered by wet/dry conditions and excluding safety-car-affected laps
- **Session history** — filterable by track, year, and weather, with one-click deletion

### FSAE (Formula Student)
- **Offline CAN log import** — reads raw CAN logs (`.asc`, `.blf`, `.trc`, `.csv`, `.mf4`, ...) pulled via USB from the car's onboard datalogger after a run, via `python-can`
- **Manual channel labeling** — no DBC file required. Every team wires its CAN IDs differently, so KOACH lets you label each signal yourself: byte range, bit length, endianness, signed/unsigned, scale, and offset — directly in the UI, with the found CAN IDs and sample bytes shown alongside for reference
- **Correctable, non-destructive decoding** — raw CAN frames are kept on disk independently of the decoded result, so a mislabeled channel can be fixed and re-decoded without re-importing the original log
- **Dynamic multi-channel graphing** — channel sets vary session to session (and team to team), so the chart screen lets you pick any subset of decoded channels and renders each on its own auto-scaled row
- **Session history on the home screen** — FSAE sessions show their labeling status (labeled / pending) and can be deleted, cascading to their database rows and Parquet files

### Shared
- **Local-first storage** — SQLite for structured metadata, Parquet for high-frequency telemetry (columnar, compressed, fast to load into charts)
- **Secure credential storage** — AI provider API keys are stored via your OS's native credential manager (Windows Credential Manager / macOS Keychain / Linux Secret Service), never written to disk in plaintext
- **Five runtime-switchable themes** — dark, light, and three accent palettes (Graphite & Mint, Porcelain & Blue, Violet & Dragonfruit), no restart required

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | PyQt6 |
| Charts | Plotly (rendered via `QWebEngineView`) |
| Structured storage | SQLite + SQLAlchemy ORM |
| Raw telemetry storage | Apache Parquet (via `pyarrow`) |
| CAN log parsing | `python-can` |
| AI providers | Groq, Anthropic, Google Gemini |
| Credential storage | `keyring` (OS-native secure storage) |
| Architecture | Hexagonal (ports & adapters) |

## Architecture

Each layer is split by module (`f125/` and `fsae/`) where the logic genuinely differs; code with no module-specific concerns (theming, credential storage, the AI adapters, the shared SQLite engine) stays at the top of its layer and is used by both.

```
f1_coach/
├── domain/                      # Pure business logic — no framework dependencies
│   ├── models/
│   │   ├── f125/                  # Session, Lap, CarSetup, TelemetryPoint, enums
│   │   ├── fsae/                  # VehicleSession, RawCanFrame, ChannelMapping, VehicleTelemetryPoint
│   │   └── profile.py             # Shared single-user profile
│   └── ports/
│       ├── f125/                  # SessionRepository, LapRepository, CarSetupRepository
│       ├── fsae/                  # VehicleSessionRepository, ChannelMappingRepository, CanLogReader
│       ├── ai_adapter.py          # Shared Protocol — provider-agnostic
│       └── profile_repository.py
├── application/
│   ├── f125/                     # CoachingEngine, TelemetryAnalyzer, PromptBuilder
│   └── fsae/                     # channel_decoder (RawCanFrame + ChannelMapping → VehicleTelemetryPoint)
├── infrastructure/                # Concrete implementations
│   ├── f125_udp/                   # Packet structs, parsers, TelemetryReceiver, SessionManager
│   ├── can/                        # python-can-based CanLogReader
│   ├── storage/
│   │   ├── orm/                     # base.py (shared Base) + f125_tables.py + fsae_tables.py
│   │   ├── mappers/                 # f125_domain_mapper.py + fsae_domain_mapper.py
│   │   ├── repositories/            # f125/ + fsae/ SQLite repository implementations
│   │   ├── f125_parquet_writer.py
│   │   └── fsae/parquet_writer.py
│   ├── ai/                          # Groq/Anthropic/Gemini adapters (shared)
│   └── security/                    # OS credential store integration (shared)
└── presentation/                  # PyQt6 UI — one file per screen
    ├── f125/                        # Landing, Live Session, Lap Analysis, Session History
    ├── fsae/                        # Landing, Import, Labeling, Chart
    └── (sidebar, theme, main_window, ana_sayfa, profil, ayarlar — shared)
```

The domain layer has zero knowledge of PyQt6, SQLAlchemy, UDP field names, or CAN bus internals — all translation happens in dedicated mapper/decoder modules, keeping the core logic testable and framework-agnostic.

---

## Getting Started

### Prerequisites

- Python 3.11+
- For the F1 25 module: F1 25 (PC) with UDP telemetry enabled in-game
- For the FSAE module: a raw CAN log file exported from your car's datalogger (no DBC file needed)

### Installation

```bash
git clone https://github.com/<your-username>/koach.git
cd koach
pip install -e .
```

### Run

```bash
python -m f1_coach.presentation.app
```

On first launch you'll be guided through creating a profile.

### F1 25 module

In-game: **Settings → Telemetry Settings**
- UDP Telemetry: **On**
- UDP Broadcast Mode: **Off**
- UDP IP Address: `127.0.0.1` (if running on the same machine)
- UDP Port: `20777` (default — configurable in KOACH's own Settings screen)

Then in KOACH:
1. Click the **F1 25** icon in the sidebar → **Başla**
2. Drive — laps are recorded automatically as they complete
3. Open **Lap Analizi** to view charts, track setup changes, and generate AI feedback (requires an API key — see below)

### FSAE module

1. Pull the raw CAN log off your datalogger's USB storage after a run
2. Click the **FSAE** icon in the sidebar → **Başla**
3. **İçe Aktar** — select the log file and give the session a name
4. **Etiketleme** — for each CAN ID you care about, define its signal(s): byte offset, bit length, endianness, signed/unsigned, scale, offset, name, and unit. Click a row in the found-IDs table to autofill its ID into the form. Save & decode when done — you can come back and correct a mapping later without re-importing the file
5. **Grafik** — pick any combination of decoded channels to plot, each on its own row
6. **Session'ı Bitir** to return home — the session (and its labeling status) appears under "Son FSAE Session'ları"

### AI Provider Setup (F1 25 coaching)

Go to **Settings**, choose a provider, and paste your API key:

| Provider | Get a key |
|---|---|
| Groq (recommended — fast, generous free tier) | https://console.groq.com/keys |
| Anthropic | https://console.anthropic.com/ |
| Gemini | https://ai.google.dev/ |

Your key is stored via your OS's credential manager — it never touches the SQLite database or any log file.

---

## Development

```bash
pip install -e ".[dev]"
```

Includes `mypy`, `ruff`, `pytest`, and `pytest-qt`.

---

## Project Status

KOACH is under active development.

**F1 25 module**
- Domain models & UDP packet parsing (verified against the official F1 25 spec)
- SQLite + Parquet storage layer
- End-to-end UDP capture pipeline
- AI coaching engine with reference-lap hierarchy and wet/dry + safety-car filtering
- Car setup change tracking across pit stops, with AI trade-off analysis
- Full PyQt6 UI — Profile, Home, Landing, Live Session, Lap Analysis, Session History, Settings

**FSAE module**
- Domain models & ports (VehicleSession, RawCanFrame, ChannelMapping)
-  `python-can`-based raw log reader (format-agnostic: `.asc`/`.blf`/`.trc`/`.csv`/`.mf4`)
-  SQLite + Parquet storage layer (raw frames kept separately from decoded telemetry, enabling correction without re-import)
-  Manual channel labeling UI with autofill from found CAN IDs
-  Dynamic multi-channel chart screen
-  Session lifecycle on the home screen (recent sessions, labeling status, delete)
-  Live telemetry ingestion (LTE/RF) — deferred; current scope is offline USB import only

**Shared**
-  Five runtime-switchable themes
-  Secure, deletable API key storage via OS credential manager

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

F1 25 module built against the official EA Sports F1 25 UDP Telemetry Specification.

---

## Credits
Track Maps: https://github.com/julesr0y/f1-circuits-svg

---
