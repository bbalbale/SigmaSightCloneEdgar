# PRD5: Instant Earnings, Filings, and Internal Doc Summaries

**Created**: December 22, 2025  
**Status**: Draft  
**Priority**: High  
**Depends On**: PRD3 (AI Consolidation), PRD4 (AI Chat Enhancements), EDGAR_FUNDAMENTALS_INTEGRATION_PLAN.md

---

## Executive Summary

Add an "instant summarize" capability for earnings releases, SEC filings (10-K/10-Q/8-K), and tenant/internal documents. The feature should fetch or ingest the source document, route it through our existing OpenAI Responses API path with RAG + tools, and return a concise, citation-backed brief that users can follow up on in chat. No core domain tables change; all artifacts live in existing AI tables (`ai_kb_documents`, `ai_memories`, `ai_feedback`) and the insights/chat flows.

---

## Goals

- Produce 60–90 second briefs for a company’s latest filing or uploaded doc with sources and key metrics.  
- Support both portfolio holdings (auto-pick latest filing) and ad-hoc ticker/doc requests.  
- Allow follow-up Q&A in chat with tool calling + RAG using the same document context.  
- Reuse existing AI infra: Responses API, `rag_service`, tool registry, SSE streaming, memory.

### Success Criteria

- <10s latency when a parsed document is already ingested; <60s with fresh fetch/parse.  
- Summaries include: headline, YoY/seq KPIs, guidance, risks/flags, and 3–5 citations.  
- Works for: (a) latest 10-K/10-Q/8-K, (b) earnings call transcript/PDF upload, (c) tenant/internal docs.  
- Chat follow-ups reuse the same doc context (no context loss between summary and Q&A).

### Non-Goals

- Creating new core domain tables or changing portfolio/position schemas.  
- Building a new search provider; we rely on EDGAR + existing data vendors + internal uploads.  
- Full-blown fine-tuning (handled separately in training-process alternatives).

---

## Current State (from PRD1–PRD4)

- Consolidated backend-only AI path (Responses API) with 18+ tools and SSE streaming (PRD3).  
- RAG service + pgvector tables (`ai_kb_documents`, `ai_memories`, `ai_feedback`) ready (PRD1 Phase 2, PRD4 memory/feedback).  
- Morning briefing and memory features already wired (PRD2/PRD4).  
- EDGAR fundamentals/doc ingestion plan exists (`PlanningDocs/EDGAR_FUNDAMENTALS_INTEGRATION_PLAN.md`) but filing summaries are not yet productized.

Gap: No end-to-end flow that (a) fetches filings/transcripts/internal docs, (b) chunks/embeds, (c) summarizes with citations, and (d) keeps the context alive for chat follow-ups.

---

## Proposed Solution Overview

**Ingestion & Storage**  
- Reuse `ai_kb_documents` for all documents. Store metadata in `metadata` JSON (ticker, cik, fiscal_year/quarter, filing_type, source_url, uploaded_by, access_scope). No new domain columns.  
- Enable two feeders: (1) EDGAR/earnings fetcher (leveraging EDGAR fundamentals plan) and (2) tenant/internal uploads (PDF/Doc).  
- Chunk + embed with `text-embedding-3-small`; push embeddings + plaintext into `ai_kb_documents` with `scope` tags like `"doc:filing"`, `"doc:transcript"`, `"doc:internal"`, `"ticker:AAPL"`.

**Retrieval & Tools**  
- New tools in `tool_registry` to access documents without altering domain schemas:
  - `list_company_documents(ticker, types?, limit?)` → latest ingested docs + metadata.
  - `get_document_chunks(document_id, sections?, limit?)` → returns ordered chunks for summarization.
  - Optional `get_key_financials(ticker, period)` can reuse existing analytics/fundamentals endpoints to inject hard numbers into summaries (no new data fields).
- Gate tools by UI context (portfolio holdings → default to that ticker; uploads → bound to tenant/user).

**Summarization Path**  
- Add a `document_summary` insight path that selects the right prompt template:
  - Filing prompt (10-K/10-Q/8-K) → headline, revenue/EPS YoY + seq, guidance, segments, liquidity/covenants, risks.  
  - Earnings call transcript prompt → tone + guidance deltas + watch items.  
  - Internal doc prompt → objective summary + action items + owners/dates (if detected).  
- Always attach citations (chunk source + URL if available) and a “data currency” note (filing date/period).  
- Stream via SSE (same contract) so the UI feels instant.

**UX Surfaces**  
- SigmaSight AI page: add "Summarize filing" CTA (auto-selects active portfolio holding) + upload for internal docs.  
- Chat: a slash command or quick action `/summarize {ticker or file}` that triggers the new path and keeps conversation context.  
- Insight card variant: display the generated summary with citations and a "Ask follow-ups" button that seeds chat with the same doc context.

---

## Architecture & Data Flow

1) **Request**: user clicks "Summarize filing" or uploads a doc; frontend posts to `/api/v1/insights/generate` (new `insight_type=document_summary`) or `/api/v1/chat/send` with `doc_request` payload (ticker|document_id|upload_ref).  
2) **Source acquisition**: backend fetches latest filing via EDGAR (if not cached) or pulls upload from storage; stores chunks + embeddings in `ai_kb_documents` with scoped metadata.  
3) **Retrieval**: `rag_service` selects top chunks using scopes derived from ticker/portfolio/tenant and doc_id.  
4) **Prompt assembly**: system prompt includes role, UI context, doc metadata (type, period, filing date), and selected chunks; tools exposed = doc tools + analytics tools + `web_search` (for corroborating fresh news).  
5) **Responses API call**: streaming response with citations; if analytics numbers are missing, the model can call `get_key_financials` to fill KPI table.  
6) **Return**: SSE to frontend; optional persistence in `AI_INSIGHTS` with type `document_summary` (no schema change, just enum addition) for reuse.

---

## Implementation Phases

### Phase 0: Prereqs & Alignment (1 day)
- Confirm EDGAR ingestion path from `EDGAR_FUNDAMENTALS_INTEGRATION_PLAN.md` (which endpoints + storage bucket).  
- Define doc metadata contract (keys inside `metadata` JSON) and scopes (`doc:*`, `ticker:*`, `tenant:*`).  
- Decide storage for uploads (reuse existing file store if present; otherwise S3/R2 bucket referenced in metadata only).

### Phase 1: Ingestion Pipelines (2–3 days)
- **Backend**: add ingestion service to pull latest 10-K/10-Q/8-K per ticker and push chunks into `ai_kb_documents`.  
- **Uploads**: add `/api/v1/agent/docs` (tenant-scoped) for PDF uploads → text extraction → chunk/embed → store in `ai_kb_documents` with `scope` = `tenant:{id}` + `doc:internal`.  
- **Batch**: nightly job to refresh filings for portfolio tickers; debounce to avoid duplicate chunks (hash-based).

### Phase 2: Tools + Retrieval (1–2 days)
- Register `list_company_documents` and `get_document_chunks` in `tool_registry` with Pydantic schemas and docstrings; reuse `rag_service` for embeddings.  
- Add simple prioritization: prefer most recent filing of requested type; fallback to closest prior period.  
- Add guardrails: enforce tenant scoping on internal docs; redact content for other tenants.

### Phase 3: Summarization Prompts & API Wiring (2 days)
- Create prompt templates in `backend/app/agent/prompts/` for filings, transcripts, and internal docs.  
- Extend `openai_service.generate_insight` (or chat path) to handle `document_summary` `insight_type` and assemble doc context + citations.  
- Optional: add lightweight KPI table by invoking existing fundamentals/analytics tools when ticker is known.

### Phase 4: Frontend UX (2–3 days)
- SigmaSight AI page: add CTA + upload flow; render summaries with citations; provide "Ask follow-ups" that seeds chat with `document_id`.  
- Chat: add quick action/slash command and show a "Doc context active" pill when doc context is loaded.  
- Ensure SSE streaming matches existing contract; add copy/regenerate hooks (ties to PRD4 Phase 4).

### Phase 5: QA, Metrics, Hardening (1–2 days)
- Tests: doc ingestion unit tests, tool schema tests, end-to-end SSE smoke for `document_summary`.  
- Observability: log doc type/ticker/period + latency; capture feedback via `ai_feedback`.  
- Caching: reuse stored summary when source doc hash unchanged; include staleness banner if older than X days.

---

## Data, Security, and Compliance Notes

- **No core schema changes**: all metadata in `ai_kb_documents.metadata`; `AI_INSIGHTS` reused with new `document_summary` type (enum update only).  
- **Access control**: enforce tenant scoping on uploads and any internal docs via metadata scopes; do not surface internal docs in global searches.  
- **Citations**: return chunk IDs + source URLs/filing dates to prove provenance.  
- **PII**: strip or mask PII in uploads before embedding if necessary (config flag).  
- **Latency**: prefetch filings for portfolio tickers to hit the <10s target; fallback to background fetch + notify user when ready.

---

## Testing & Validation Plan

- **Backend**: unit tests for ingestion service (dedupe, chunking), tool schemas, and prompt selection; integration test calling `/api/v1/insights/generate` with `document_summary`.  
- **Frontend**: TypeScript types for `document_summary`, SSE rendering tests, upload flow happy-path.  
- **Manual**: summarize latest AAPL 10-Q, a fresh 8-K, an earnings call transcript PDF, and a tenant-only PDF; verify citations and chat follow-ups.

---

## Risks & Mitigations

- **Parsing quality varies**: use robust PDF/text extraction and allow user-visible source links; keep chunk size moderate to reduce noise.  
- **Latency on first-time filings**: prefetch for tracked tickers; allow async job with toast/notification when ready.  
- **Data leakage across tenants**: strict scope filtering in retrieval and tools; include tenant checks in tool handlers.  
- **Hallucinated metrics**: prefer tool calls for KPIs; require citations in prompt; show "data currency" timestamp.  
- **Large uploads**: set size limits and fall back to server-side chunk streaming.

---

## Open Questions

- Should we also surface summaries as saved insights in the left panel, or only via chat?  
- Do we need an admin UI to manage ingested docs (reprocess/delete/mark stale)?  
- What storage is available for uploads today (S3/R2/local)? If none, add a minimal bucket + signed URL approach.

