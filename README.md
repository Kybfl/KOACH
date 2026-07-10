# KOACH

<img width="400" alt="koach_siyah" src="https://github.com/user-attachments/assets/fe0823af-b6aa-43ad-9f8a-8d722ef38ba6" />

**F1 25 telemetry analysis and AI-powered post-session coaching — a native desktop app.**

KOACH listens to F1 25's UDP telemetry broadcast, stores every lap locally, visualizes speed/throttle/brake traces with interactive charts, and generates sector-based AI coaching feedback after each session — entirely passive, with zero interference with the game.

---

## Features

- **Real-time UDP telemetry capture** — listens on port 20777 (configurable), parses official F1 25 packet structures via `ctypes`
- **Local-first storage** — SQLite for structured metadata, Parquet for high-frequency raw telemetry (~60 samples/sec per lap)
- **Interactive lap analysis** — Plotly-powered speed, throttle/brake overlay, and gear charts, aligned by track position (0.0–1.0) for accurate lap comparison
- **AI coaching feedback** — sector-based, statistically-grounded post-lap and post-session analysis via Groq, Anthropic, or Gemini (your choice, your API key)
- **Reference lap hierarchy** — compares against session-best, then track-best, filtered by wet/dry conditions and excluding safety-car-affected laps
- **Session history** — filterable by track, year, and weather, with one-click deletion
- **Secure credential storage** — API keys are stored via your OS's native credential manager (Windows Credential Manager / macOS Keychain / Linux Secret Service), never written to disk in plaintext
- **Live/dark theme** — switchable at runtime, no restart required
  
---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | PyQt6 |
| Charts | Plotly (rendered via `QWebEngineView`) |
| Structured storage | SQLite + SQLAlchemy ORM |
| Raw telemetry storage | Apache Parquet (via `pyarrow`) |
| AI providers | Groq, Anthropic, Google Gemini |
| Credential storage | `keyring` (OS-native secure storage) |
| Architecture | Hexagonal (ports & adapters) |

## Architecture

```
f1_coach/
├── domain/            # Pure business logic — no framework dependencies
│   ├── models/         # Session, Lap, TelemetryPoint, Profile, enums
│   └── ports/           # Protocol interfaces (SessionRepository, AIAdapter, ...)
├── application/        # Orchestration — CoachingEngine, TelemetryAnalyzer, PromptBuilder
├── infrastructure/      # Concrete implementations
│   ├── udp/              # Packet structs, parsers, TelemetryReceiver, SessionManager
│   ├── storage/          # SQLAlchemy models, repositories, Parquet writer
│   ├── ai/                # Groq/Anthropic/Gemini adapters
│   └── security/         # OS credential store integration
└── presentation/        # PyQt6 UI — one file per screen, theme system
```

The domain layer has zero knowledge of PyQt6, SQLAlchemy, or any UDP field name — all translation happens in dedicated mapper modules, keeping the core logic testable and framework-agnostic.

---

## Getting Started

### Prerequisites

- Python 3.11+
- F1 25 (PC) with UDP telemetry enabled in-game

### Installation

```bash
git clone https://github.com/<your-username>/koach.git
cd koach
pip install -e .
```

### Configure F1 25

In-game: **Settings → Telemetry Settings**
- UDP Telemetry: **On**
- UDP Broadcast Mode: **Off**
- UDP IP Address: `127.0.0.1` (if running on the same machine)
- UDP Port: `20777` (default — configurable in KOACH's own Settings screen)

### Run

```bash
python -m f1_coach.presentation.app
```

On first launch you'll be guided through creating a profile. From there:
1. Click the **F1 25** icon in the sidebar
2. Click **Başla** to start listening
3. Drive — laps are recorded automatically as they complete
4. Open **Lap Analizi** to view charts and generate AI feedback (requires an API key — see below)

### AI Provider Setup

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

KOACH is under active development. Completed so far:

- ✅ Domain models & UDP packet parsing (verified against the official F1 25 spec)
- ✅ SQLite + Parquet storage layer
- ✅ End-to-end UDP capture pipeline
- ✅ AI coaching engine with reference-lap hierarchy and wet/dry + safety-car filtering
- ✅ Full PyQt6 UI — Profile, Home, F1 25 Landing, Live Session, Lap Analysis, Session History, Settings
- ✅ Runtime dark/light theme switching
- AI-assisted setups: Coming soon.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Built against the official EA Sports F1 25 UDP Telemetry Specification.
