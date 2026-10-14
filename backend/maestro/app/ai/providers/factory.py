"""
Provider factory for MAESTRO AI runtime.

Keeps concrete provider construction out of the execution pipeline so future
providers can be added without changing orchestration code.
"""
from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.google import GoogleProvider


def get_llm_provider(provider_name: str) -> BaseLLMProvider:
    provider = provider_name.lower()
    if provider == "google":
        return GoogleProvider()
    raise ValueError(f"Unsupported AI provider: {provider_name}")
