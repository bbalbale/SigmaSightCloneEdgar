# Backend
- Don't see a script to pull company profiles

# Sandbox
- Cron jobs in Railway Sandbox are not occuring - docker instance is crashing

# Target Price
- Target prices need to be aggregated and saved to create a portfolio target return for lons/shorts/optons and the rest of the portfolio. Portfolio Returns are now being calculated only on the frontend

# Chat
- We have two version of chat running now.

## Backend System (/app/agent/ and /app/api/v1/chat/):
- Uses OpenAI Responses API (different from Chat Completions)
- Server-side API key management (secure)
- Conversation persistence in PostgreSQL database
- User authentication & authorization per conversation
- Centralized rate limiting and cost control
- Audit trail and logging of all AI interactions
- Tools have direct database access for complex operations
- Production-ready with retry logic, fallbacks, error handling

## Frontend System (just built):
- Uses OpenAI Chat Completions API (direct from browser)
- API key exposed in browser code (less secure)
- Conversations only in Zustand/localStorage (ephemeral)
- No server-side logging or auditing
- Tools limited to what frontend services can access
- Simpler, faster for demos and prototyping
