"""
LLM Providers Package
Provides implementations for different LLM providers
Part of Phase 10.3: Multi-LLM Support Foundation
"""

from .openai_provider import OpenAIProvider

__all__ = ["OpenAIProvider"]

# Provider registry for future expansion
PROVIDERS = {
    "openai": OpenAIProvider,
    # Future providers can be added here:
    # "anthropic": AnthropicProvider,
    # "google": GoogleProvider,
    # "cohere": CohereProvider,
}

def get_provider(provider_name: str):
    """
    Get a provider instance by name.
    
    Args:
        provider_name: Name of the provider (e.g., 'openai')
        
    Returns:
        Provider instance
        
    Raises:
        ValueError: If provider not found
    """
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    return provider_class()