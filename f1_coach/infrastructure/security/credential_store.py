"""İşletim sistemi credential store'u üzerinden API key saklama.

Windows'ta Credential Manager, macOS'ta Keychain, Linux'ta Secret Service
kullanır — API key hiçbir zaman düz metin olarak SQLite'a yazılmaz.

keyring backend'i bazı ortamlarda (ör. headless Linux) kurulu olmayabilir;
bu durumda hatalar yutulur ve loglanır, uygulama çökmez — yalnızca AI
özellikleri yapılandırılamamış gibi davranır.
"""

import keyring

from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_SERVICE_NAME = "koach"


def save_api_key(provider: str, api_key: str) -> None:
    """Belirtilen sağlayıcı için API key'i güvenli şekilde saklar."""
    try:
        keyring.set_password(_SERVICE_NAME, provider, api_key)
    except Exception as exc:
        logger.error("API key kaydedilemedi (provider=%s): %s", provider, exc)


def get_api_key(provider: str) -> str:
    """Belirtilen sağlayıcı için saklanan API key'i döner, yoksa boş string."""
    try:
        return keyring.get_password(_SERVICE_NAME, provider) or ""
    except Exception as exc:
        logger.warning("API key okunamadı (provider=%s): %s", provider, exc)
        return ""


def has_api_key(provider: str) -> bool:
    """Belirtilen sağlayıcı için geçerli bir API key kayıtlı mı?"""
    return bool(get_api_key(provider))