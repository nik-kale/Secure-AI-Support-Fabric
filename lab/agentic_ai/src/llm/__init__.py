"""
LLM Integration Module
Supports multiple LLM providers for advanced anomaly detection
"""
from .base import LLMProvider, LLMConfig
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .local_provider import LocalProvider
from .guardrails import InputGuardrail, OutputGuardrail
from .prompt_library import PromptLibrary

__all__ = [
    'LLMProvider',
    'LLMConfig',
    'AnthropicProvider',
    'OpenAIProvider',
    'LocalProvider',
    'InputGuardrail',
    'OutputGuardrail',
    'PromptLibrary'
]


def create_provider(provider_name: str = 'anthropic', **kwargs) -> LLMProvider:
    """
    Factory function to create LLM provider

    Args:
        provider_name: 'anthropic', 'openai', or 'local'
        **kwargs: Provider-specific configuration

    Returns:
        LLMProvider instance
    """
    providers = {
        'anthropic': AnthropicProvider,
        'openai': OpenAIProvider,
        'local': LocalProvider
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")

    return provider_class(**kwargs)
