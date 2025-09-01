# Agent Module

> **Updated for V1.1 Chat Implementation - Mixed Auth & Enhanced Features**

**V1.1 Key Changes**:
- **Authentication**: Mixed strategy (JWT for portfolio, HttpOnly cookies for chat)
- **Streaming**: fetch() POST with credentials:'include' replaces EventSource
- **Frontend Stores**: Split architecture (chatStore for data, streamStore for runtime)
- **Message Queue**: One in-flight per conversation with queue cap=1
- **Error Handling**: Enhanced taxonomy with retryable classification
- **Performance**: TTFB metrics and observability hooks

See `_docs/` for detailed implementation guides updated for V1.1.
