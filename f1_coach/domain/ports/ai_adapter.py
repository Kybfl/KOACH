"""AIAdapter port — the boundary between the application and AI providers.

Groq, Anthropic, and Gemini implementations all satisfy this Protocol.
The application layer only ever calls ``generate_feedback``; provider-specific
authentication, retry logic, and token counting are encapsulated in the adapters.
"""

from typing import Protocol


class AIAdapter(Protocol):
    """Contract for AI provider adapters."""

    def generate_feedback(self, prompt: str) -> str:
        """Send a prompt to the underlying AI provider and return the response.

        Args:
            prompt: The fully-assembled coaching prompt produced by PromptBuilder.

        Returns:
            The raw text response from the AI provider.

        Raises:
            RuntimeError: If the provider returns an error or times out after
                          all retry attempts are exhausted.
        """
        ...
