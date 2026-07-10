"""Gemini AI adapter.

Satisfies the AIAdapter Protocol structurally — no inheritance required.
"""

import google.generativeai as genai

from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiAdapter:
    """AIAdapter implementation backed by the Google Gemini API."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def generate_feedback(self, prompt: str) -> str:
        """Send the prompt to Gemini and return the generated feedback text.

        Raises:
            RuntimeError: If the Gemini API call fails.
        """
        try:
            response = self._model.generate_content(prompt)
            text = getattr(response, "text", None)
            if not text:
                raise RuntimeError("Gemini returned an empty response.")
            return text.strip()
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            raise RuntimeError(f"Gemini feedback generation failed: {exc}") from exc
