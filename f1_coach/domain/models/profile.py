"""Profile domain model.

KOACH is a single-user local application, so there is conceptually only
ever one Profile row. It exists so the app can distinguish "first launch"
(no profile yet → route to Profil page) from "returning user" (profile
exists → route straight to Ana Sayfa).

API key is NOT stored here — see infrastructure/security/credential_store.py.
Only the provider name is kept so the app knows which credential to look up.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Profile:
    """The single user profile for this local KOACH installation.

    Attributes:
        name:            Display name shown in "Hoş geldin [Ad]" greeting.
        email:           User's email address.
        favorite_team:   Selected from a fixed dropdown list in the UI.
        favorite_driver: Selected from a fixed dropdown list in the UI.
        favorite_track:  Selected from a fixed dropdown list in the UI.
        photo_path:      Absolute path to the user's uploaded photo file.
                         Empty string if no photo has been uploaded.
        ai_provider:     "groq" | "anthropic" | "gemini", empty if unconfigured.
        udp_port:        UDP port to listen on for F1 25 telemetry.
        theme:           "dark" | "light".
        created_at:      When the profile was first created (onboarding).
        id:              Database primary key; -1 means not yet persisted.
    """

    name: str
    email: str
    favorite_team: str = field(default="")
    favorite_driver: str = field(default="")
    favorite_track: str = field(default="")
    photo_path: str = field(default="")
    ai_provider: str = field(default="")
    udp_port: int = field(default=20777)
    theme: str = field(default="dark")
    ui_scale: float = field(default=1.0)
    created_at: datetime = field(default_factory=datetime.now)
    id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1

    @property
    def is_ai_configured(self) -> bool:
        """True if a provider has been selected (API key check is separate —
        see credential_store.has_api_key, which requires an I/O call)."""
        return bool(self.ai_provider)