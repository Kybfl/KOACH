"""Anthropic AI adapter.

Satisfies the AIAdapter Protocol structurally — no inheritance required.
"""

from anthropic import Anthropic

from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 800


class AnthropicAdapter:
    """AIAdapter implementation backed by the Anthropic API."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def generate_feedback(self, prompt: str) -> str:
        """Send the prompt to Claude and return the generated feedback text.

        Raises:
            RuntimeError: If the Anthropic API call fails.
        """
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            text_blocks = [block.text for block in response.content if block.type == "text"]
            text = "\n".join(text_blocks).strip()
            if not text:
                raise RuntimeError("Anthropic returned an empty response.")
            return text
        except Exception as exc:
            logger.error("Anthropic API call failed: %s", exc)
            raise RuntimeError(f"Anthropic feedback generation failed: {exc}") from exc
