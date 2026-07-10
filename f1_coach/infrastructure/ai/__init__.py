"""AI provider adapters — all satisfy the AIAdapter Protocol."""

from f1_coach.infrastructure.ai.adapter_factory import create_ai_adapter
from f1_coach.infrastructure.ai.anthropic_adapter import AnthropicAdapter
from f1_coach.infrastructure.ai.gemini_adapter import GeminiAdapter
from f1_coach.infrastructure.ai.groq_adapter import GroqAdapter

__all__ = ["create_ai_adapter", "GroqAdapter", "AnthropicAdapter", "GeminiAdapter"]
