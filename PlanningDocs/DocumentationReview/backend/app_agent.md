# App Agent Directory Documentation

This document describes all files in `backend/app/agent/` and its subdirectories.

---

## Overview

The `app/agent/` module implements the AI agent system using OpenAI's Responses API for investment analytics and portfolio reasoning. It provides a provider-agnostic architecture with OpenAI as the current implementation.

---

## Root Level: `app/agent/`

### `__init__.py`
Empty package initialization file that allows the agent module to be imported as a Python package. Used implicitly by Python whenever `from app.agent import ...` statements execute.

### `llm_client.py`
Defines the `LLMClient` protocol (interface) and a singleton factory function `get_llm_client()` that abstracts provider-specific LLM implementations. Imported by `llm_openai.py` and `api/v1/chat/send.py`.

### `llm_openai.py`
Implements `OpenAILLMClient` class that wraps the `OpenAIService` and conforms to the `LLMClient` protocol for streaming responses. Imported by `llm_client.py` and `api/v1/chat/send.py`.

---

## `adapters/` Subdirectory

### `__init__.py`
Empty package initialization file for the adapters module. Used by Python import system.

### `openai_adapter.py`
Provides `OpenAIToolAdapter` class that converts provider-neutral portfolio tool definitions to OpenAI function-calling JSON schema format. Used by `openai_service.py` for tool schema generation and execution.

---

## `models/` Subdirectory

### `__init__.py`
Package initialization that exports `Conversation`, `ConversationMessage`, `UserPreference`. Used by model imports throughout the application.

### `conversations.py`
Defines SQLAlchemy ORM models for storing AI conversations and individual messages in the Core database (`agent_conversations` and `agent_messages` tables). Imported by 21+ files including chat endpoints, admin endpoints, and learning service.

### `preferences.py`
Defines `UserPreference` SQLAlchemy model for storing per-user agent configuration including default mode, model selection, and feature toggles. Imported by administrative and user preference endpoints.

---

## `schemas/` Subdirectory

### `__init__.py`
Package initialization that exports all Pydantic request/response schemas for agent operations. Used for endpoint imports.

### `base.py`
Defines `AgentBaseSchema` as the base Pydantic model for all agent schemas with common configuration including datetime serialization to ISO8601 and UUID string conversion. Inherited by all other agent schemas.

### `chat.py`
Defines Pydantic request/response schemas for conversation management and messaging endpoints (`ConversationCreate`, `MessageSend`, `MessageResponse`, etc.). Imported by `api/v1/chat/conversations.py` and `api/v1/chat/send.py`.

### `sse.py`
Defines Pydantic schemas for Server-Sent Events (SSE) streaming format used for real-time streaming responses (`SSETokenEvent`, `SSEErrorEvent`, `SSEDoneEvent`, etc.). Imported by `services/openai_service.py` for serialization.

---

## `services/` Subdirectory

### `openai_service.py`
Implements the core OpenAI Responses API integration, managing message streaming, tool execution, RAG context injection, memory retrieval, and smart routing for model selection. Imported by `llm_openai.py` and `api/v1/chat/send.py`.

### `rag_service.py`
Provides semantic search over the `ai_kb_documents` table using pgvector embeddings and OpenAI text-embedding-3-small model for RAG context injection. Imported by `openai_service.py` and `learning_service.py`.

### `memory_service.py`
Provides CRUD operations for the `ai_memories` table storing user preferences, learned rules, and cross-session context. Imported by `openai_service.py`, `learning_service.py`, and memory endpoints.

### `learning_service.py`
Orchestrates the feedback learning loop (Phase 3.2 of PRD4), processing user feedback to store positive examples in RAG and extract preference rules into memories. Imported by `batch/feedback_learning_job.py`.

### `feedback_analyzer.py`
Analyzes user feedback patterns to extract learning rules using both rule-based heuristics and LLM-based extraction from edited responses. Imported by `learning_service.py` for rule extraction.

---

## `tools/` Subdirectory

### `__init__.py`
Empty package initialization file for the tools module. Used by Python import system.

### `handlers.py`
Implements `PortfolioTools` class containing provider-neutral business logic for fetching and formatting portfolio data through internal API calls (20+ tools). Imported by `tool_registry.py` and `openai_adapter.py`.

### `tool_registry.py`
Central registry for all tools with uniform dispatch and SSE envelope handling, implementing the ultra-thin handler pattern (22 registered tools). Imported by `openai_service.py` to dispatch tool calls.

---

## `prompts/` Subdirectory

### `prompt_manager.py`
Manages loading and caching of system prompts for the investment analyst agent, with fallback handling if prompt files are missing. Imported by `openai_service.py` during prompt preparation.

---

## Summary Table

| File | Main Responsibility | Used By |
|------|---------------------|---------|
| `llm_client.py` | LLM provider abstraction & singleton factory | `llm_openai.py`, chat endpoints |
| `llm_openai.py` | OpenAI Responses API wrapper | `llm_client.py` factory, chat endpoints |
| `adapters/openai_adapter.py` | Tool schema conversion & execution | `openai_service.py` |
| `models/conversations.py` | Chat conversation storage | 20+ files including chat/admin endpoints |
| `models/preferences.py` | User agent configuration storage | Admin/preference endpoints |
| `schemas/base.py` | Base schema with common config | All other schemas |
| `schemas/chat.py` | Request/response schemas for conversations | Chat endpoints |
| `schemas/sse.py` | SSE streaming event schemas | `openai_service.py` |
| `services/openai_service.py` | OpenAI Responses API + RAG + memories | `llm_openai.py`, chat endpoints |
| `services/rag_service.py` | Semantic search with embeddings | `openai_service.py`, `learning_service.py` |
| `services/memory_service.py` | User memory CRUD & formatting | `openai_service.py`, `learning_service.py`, endpoints |
| `services/learning_service.py` | Feedback learning orchestration | Feedback batch job |
| `services/feedback_analyzer.py` | Feedback pattern analysis | `learning_service.py` |
| `tools/handlers.py` | Portfolio data access logic (provider-neutral) | `tool_registry.py`, `openai_adapter.py` |
| `tools/tool_registry.py` | Central tool dispatch & envelope | `openai_service.py` |
| `prompts/prompt_manager.py` | System prompt loading & caching | `openai_service.py` |

---

## Architecture Patterns

**Provider-Agnostic Design**: 95% of code in `handlers.py` is provider-neutral; only 5% in adapters is provider-specific.

**Dual Database Usage**:
- Core DB: Conversations, messages (via `Conversation`, `ConversationMessage` models)
- AI DB: RAG documents, memories, feedback (via RAG/memory services)

**SSE Streaming**: All responses streamed via Server-Sent Events with standardized event envelope for real-time frontend updates.

**Feedback Loop**: Positive feedback → RAG examples, Negative feedback → Memory rules for continuous agent improvement.
