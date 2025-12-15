"""
LLM Client Protocol - Provider-agnostic interface for LLM calls

This module defines the LLMClient protocol that abstracts LLM providers,
allowing SigmaSight to switch between OpenAI, Claude, or other providers
without changing endpoint code.

Per SIGMASIGHT_AGENT_EXECUTION_PLAN.md:
- Default provider: OpenAI (Responses API)
- Future providers: Claude (optional)

Usage:
    from app.agent.llm_client import get_llm_client

    client = get_llm_client()
    async for event in client.stream_response(messages, tools):
        yield format_sse_event(event)
"""

from typing import AsyncIterator, Protocol, Any, Dict, List, Optional
from enum import Enum

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient(Protocol):
    """
    Protocol defining the interface for LLM providers.

    All LLM implementations must conform to this interface to ensure
    consistent behavior across providers.
    """

    @property
    def provider(self) -> LLMProvider:
        """Return the provider identifier"""
        ...

    async def stream_response(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] | None = None,
        model: str | None = None,
        metadata: Dict[str, Any] | None = None,
        conversation_id: str | None = None,
        conversation_mode: str = "green",
        portfolio_context: Dict[str, Any] | None = None,
        auth_context: Dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream a response from the LLM provider.

        Yields SSE-formatted events compatible with our frontend:
        - start: Stream initialization
        - token: Text delta
        - tool_call: Tool invocation started
        - tool_result: Tool execution completed
        - done: Stream complete
        - error: Error occurred

        Args:
            messages: List of conversation messages
            tools: List of tool definitions (optional)
            model: Model override (optional, uses default if not provided)
            metadata: Additional metadata for the request
            conversation_id: Conversation UUID for tracking
            conversation_mode: Mode for prompt selection (e.g., 'green', 'blue')
            portfolio_context: Portfolio context dict with portfolio_id, etc.
            auth_context: Authentication context for tool execution

        Yields:
            SSE-formatted event strings ready to send to client
        """
        ...


# Singleton cache for client instances
_client_cache: Dict[LLMProvider, LLMClient] = {}


def get_llm_client(provider: LLMProvider | None = None) -> LLMClient:
    """
    Get an LLM client instance for the specified provider.

    Uses singleton pattern to reuse client instances.

    Args:
        provider: Which LLM provider to use. Defaults to settings.LLM_PROVIDER
                  or OPENAI if not configured.

    Returns:
        An LLMClient instance for the requested provider

    Raises:
        ValueError: If the provider is not supported
    """
    # Determine provider from settings if not specified
    if provider is None:
        provider_str = getattr(settings, 'LLM_PROVIDER', 'openai').lower()
        try:
            provider = LLMProvider(provider_str)
        except ValueError:
            logger.warning(f"Unknown LLM_PROVIDER '{provider_str}', defaulting to OpenAI")
            provider = LLMProvider.OPENAI

    # Check cache first
    if provider in _client_cache:
        return _client_cache[provider]

    # Create new client instance
    if provider == LLMProvider.OPENAI:
        from app.agent.llm_openai import OpenAILLMClient
        client = OpenAILLMClient()
        _client_cache[provider] = client
        logger.info(f"[LLM] Initialized OpenAI client")
        return client

    elif provider == LLMProvider.ANTHROPIC:
        # Claude implementation - placeholder for future
        raise NotImplementedError(
            "Anthropic/Claude provider not yet implemented. "
            "Per SIGMASIGHT_AGENT_EXECUTION_PLAN.md, OpenAI is the default provider."
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def clear_client_cache():
    """Clear the client cache. Useful for testing."""
    global _client_cache
    _client_cache = {}
    logger.debug("[LLM] Client cache cleared")
