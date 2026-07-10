"""AI adapter factory.

Constructs the AIAdapter implementation matching the user's configured
provider. Called once at application startup with values read from config
(provider name + API key), not on every feedback request.
"""

from f1_coach.domain.ports.ai_adapter import AIAdapter
from f1_coach.infrastructure.ai.anthropic_adapter import AnthropicAdapter
from f1_coach.infrastructure.ai.gemini_adapter import GeminiAdapter
from f1_coach.infrastructure.ai.groq_adapter import GroqAdapter

_SUPPORTED_PROVIDERS = ("groq", "anthropic", "gemini")


def create_ai_adapter(provider: str, api_key: str) -> AIAdapter:
    """Instantiate the AIAdapter for the given provider.

    Args:
        provider: One of "groq" (recommended), "anthropic", "gemini".
        api_key:  The user's API key for that provider, read from settings.

    Returns:
        An object satisfying the AIAdapter Protocol.

    Raises:
        ValueError: If the provider name is not recognised or api_key is empty.
    """
    normalised = provider.strip().lower()
    if not api_key:
        raise ValueError(f"No API key configured for provider '{provider}'.")

    if normalised == "groq":
        return GroqAdapter(api_key=api_key)
    if normalised == "anthropic":
        return AnthropicAdapter(api_key=api_key)
    if normalised == "gemini":
        return GeminiAdapter(api_key=api_key)

    raise ValueError(
        f"Unknown AI provider '{provider}'. Supported providers: {_SUPPORTED_PROVIDERS}"
    )
