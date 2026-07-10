"""Groq AI adapter.

Groq is the recommended default provider (free tier, fast 70B inference).
Satisfies the AIAdapter Protocol structurally — no inheritance required.
"""

from groq import Groq

from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 800
_TEMPERATURE = 0.4


class GroqAdapter:
    """AIAdapter implementation backed by the Groq API."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._client = Groq(api_key=api_key)
        self._model = model

    def generate_feedback(self, prompt: str) -> str:
        """Send the prompt to Groq and return the generated feedback text.

        Raises:
            RuntimeError: If the Groq API call fails.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
            )
            text = response.choices[0].message.content
            if not text:
                raise RuntimeError("Groq returned an empty response.")
            return text.strip()
        except Exception as exc:
            logger.error("Groq API call failed: %s", exc)
            raise RuntimeError(f"Groq feedback generation failed: {exc}") from exc
