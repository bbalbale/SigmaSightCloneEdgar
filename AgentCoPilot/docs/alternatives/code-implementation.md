# SigmaSight AI Learning Infrastructure: Code Implementation Guide

This document outlines the code needed to build a RAG + Feedback + Fine-tuning pipeline for SigmaSight.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAILWAY STACK                            │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL                                                      │
│  ├── pgvector extension (RAG knowledge base)                    │
│  ├── training_examples table (curated fine-tuning data)         │
│  ├── interaction_logs table (raw feedback collection)           │
│  └── knowledge_documents table (embedded domain knowledge)      │
├─────────────────────────────────────────────────────────────────┤
│  Python Backend                                                  │
│  ├── /api/chat - Main chat endpoint with RAG                    │
│  ├── /api/feedback - Capture user signals                       │
│  ├── /api/admin/curate - Promote examples to training set       │
│  └── /api/admin/export - Export JSONL for fine-tuning           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OPENAI API                               │
│  ├── text-embedding-3-small (embeddings for RAG)                │
│  ├── gpt-4o-mini (base model / fine-tuned model)                │
│  └── Fine-tuning API (training jobs)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Database Schema

### Enable pgvector Extension

```sql
-- Run once on your Railway Postgres instance
CREATE EXTENSION IF NOT EXISTS vector;
```

### Core Tables

```sql
-- Knowledge base for RAG retrieval
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(100), -- 'sec_filing', 'internal_doc', 'curated_qa'
    source_ref VARCHAR(500), -- e.g., 'NVDA/10-K/2024', URL, etc.
    embedding vector(1536), -- OpenAI text-embedding-3-small dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast similarity search
CREATE INDEX ON knowledge_documents 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Raw interaction logs (capture everything)
CREATE TABLE interaction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID,
    user_id UUID,
    
    -- The conversation
    system_prompt TEXT,
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    
    -- RAG context used
    retrieved_doc_ids UUID[],
    retrieved_context TEXT,
    
    -- Model info
    model_used VARCHAR(100), -- 'gpt-4o-mini', 'ft:gpt-4o-mini:...'
    
    -- Feedback signals
    feedback_rating INTEGER, -- -1, 0, 1 (thumbs down, none, thumbs up)
    feedback_text TEXT,
    user_edited_response TEXT, -- if user corrected the response
    had_followup BOOLEAN DEFAULT FALSE, -- did user ask clarifying question?
    
    -- Metadata
    latency_ms INTEGER,
    token_count_input INTEGER,
    token_count_output INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON interaction_logs (created_at DESC);
CREATE INDEX ON interaction_logs (feedback_rating) WHERE feedback_rating IS NOT NULL;

-- Curated training examples (promoted from interaction_logs)
CREATE TABLE training_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_interaction_id UUID REFERENCES interaction_logs(id),
    
    -- The training pair
    system_prompt TEXT NOT NULL,
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL, -- may be edited version
    
    -- Curation metadata
    category VARCHAR(100), -- 'sec_filing', 'gaap_reconciliation', 'analyst_estimates'
    quality_score INTEGER DEFAULT 5, -- 1-10, for prioritizing
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(100),
    approved_at TIMESTAMPTZ,
    
    -- Training job tracking
    included_in_jobs UUID[], -- which fine-tuning jobs used this
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON training_examples (is_approved, quality_score DESC);
CREATE INDEX ON training_examples (category);

-- Fine-tuning job history
CREATE TABLE fine_tuning_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    openai_job_id VARCHAR(100) NOT NULL,
    openai_file_id VARCHAR(100),
    
    -- Job details
    base_model VARCHAR(100) NOT NULL,
    fine_tuned_model VARCHAR(200), -- populated when complete
    
    -- Training set info
    example_count INTEGER,
    example_ids UUID[],
    
    -- Status tracking
    status VARCHAR(50), -- 'pending', 'running', 'succeeded', 'failed'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- Results
    training_loss FLOAT,
    validation_loss FLOAT,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 2. Python Backend Code

### Dependencies

```txt
# requirements.txt additions
openai>=1.0.0
pgvector>=0.2.0
asyncpg>=0.29.0
numpy>=1.24.0
```

### Configuration

```python
# config.py
import os
from dataclasses import dataclass

@dataclass
class AIConfig:
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"  # or your fine-tuned model ID
    fine_tuned_model: str = os.getenv("FINE_TUNED_MODEL_ID", None)
    
    # RAG settings
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.7
    
    # System prompt for SigmaSight
    system_prompt: str = """You are a financial analyst assistant for SigmaSight, 
specializing in SEC filings, earnings analysis, and financial metrics.

When answering questions:
- Cite specific sources (10-K, 10-Q, 8-K filings) when available
- Distinguish between GAAP and non-GAAP metrics clearly
- Break down stock-based compensation by category when relevant
- Compare analyst estimates vs reported actuals when asked
- Use precise numbers with appropriate units

If you're uncertain about specific figures, say so rather than guessing."""

config = AIConfig()
```

### Embedding Service

```python
# services/embeddings.py
from openai import OpenAI
import numpy as np
from config import config

client = OpenAI(api_key=config.openai_api_key)

def get_embedding(text: str) -> list[float]:
    """Generate embedding for a text string."""
    response = client.embeddings.create(
        model=config.embedding_model,
        input=text
    )
    return response.data[0].embedding

def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    response = client.embeddings.create(
        model=config.embedding_model,
        input=texts
    )
    return [item.embedding for item in response.data]
```

### RAG Service

```python
# services/rag.py
import asyncpg
from services.embeddings import get_embedding
from config import config

async def retrieve_relevant_context(
    query: str,
    pool: asyncpg.Pool,
    top_k: int = None,
    threshold: float = None
) -> tuple[str, list[str]]:
    """
    Retrieve relevant documents for a query.
    Returns: (formatted_context, list_of_doc_ids)
    """
    top_k = top_k or config.rag_top_k
    threshold = threshold or config.rag_similarity_threshold
    
    # Get query embedding
    query_embedding = get_embedding(query)
    
    # Search for similar documents
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id,
                title,
                content,
                source,
                source_ref,
                1 - (embedding <=> $1::vector) as similarity
            FROM knowledge_documents
            WHERE 1 - (embedding <=> $1::vector) > $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """, query_embedding, threshold, top_k)
    
    if not rows:
        return "", []
    
    # Format context for prompt
    context_parts = []
    doc_ids = []
    
    for row in rows:
        doc_ids.append(str(row['id']))
        context_parts.append(
            f"[Source: {row['source_ref'] or row['source']}]\n{row['content']}"
        )
    
    formatted_context = "\n\n---\n\n".join(context_parts)
    
    return formatted_context, doc_ids
```

### Chat Service

```python
# services/chat.py
import time
import uuid
from openai import OpenAI
import asyncpg
from services.rag import retrieve_relevant_context
from config import config

client = OpenAI(api_key=config.openai_api_key)

async def chat_with_context(
    user_message: str,
    pool: asyncpg.Pool,
    session_id: str = None,
    user_id: str = None
) -> dict:
    """
    Process a chat message with RAG context and log the interaction.
    """
    start_time = time.time()
    
    # Retrieve relevant context
    context, doc_ids = await retrieve_relevant_context(user_message, pool)
    
    # Build messages
    messages = [
        {"role": "system", "content": config.system_prompt}
    ]
    
    if context:
        messages.append({
            "role": "system", 
            "content": f"Relevant context from knowledge base:\n\n{context}"
        })
    
    messages.append({"role": "user", "content": user_message})
    
    # Choose model (fine-tuned if available)
    model = config.fine_tuned_model or config.chat_model
    
    # Call OpenAI
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=2000
    )
    
    assistant_response = response.choices[0].message.content
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Log the interaction
    interaction_id = await log_interaction(
        pool=pool,
        session_id=session_id,
        user_id=user_id,
        system_prompt=config.system_prompt,
        user_message=user_message,
        assistant_response=assistant_response,
        retrieved_doc_ids=doc_ids,
        retrieved_context=context,
        model_used=model,
        latency_ms=latency_ms,
        token_count_input=response.usage.prompt_tokens,
        token_count_output=response.usage.completion_tokens
    )
    
    return {
        "response": assistant_response,
        "interaction_id": str(interaction_id),
        "sources_used": len(doc_ids),
        "model": model,
        "latency_ms": latency_ms
    }

async def log_interaction(
    pool: asyncpg.Pool,
    **kwargs
) -> uuid.UUID:
    """Log an interaction to the database."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO interaction_logs (
                session_id, user_id, system_prompt, user_message,
                assistant_response, retrieved_doc_ids, retrieved_context,
                model_used, latency_ms, token_count_input, token_count_output
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
            RETURNING id
        """,
            kwargs.get('session_id'),
            kwargs.get('user_id'),
            kwargs.get('system_prompt'),
            kwargs.get('user_message'),
            kwargs.get('assistant_response'),
            kwargs.get('retrieved_doc_ids'),
            kwargs.get('retrieved_context'),
            kwargs.get('model_used'),
            kwargs.get('latency_ms'),
            kwargs.get('token_count_input'),
            kwargs.get('token_count_output')
        )
        return row['id']
```

### Feedback Service

```python
# services/feedback.py
import asyncpg

async def record_feedback(
    pool: asyncpg.Pool,
    interaction_id: str,
    rating: int = None,  # -1, 0, 1
    feedback_text: str = None,
    edited_response: str = None
) -> bool:
    """Record user feedback for an interaction."""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE interaction_logs
            SET 
                feedback_rating = COALESCE($2, feedback_rating),
                feedback_text = COALESCE($3, feedback_text),
                user_edited_response = COALESCE($4, user_edited_response)
            WHERE id = $1
        """, interaction_id, rating, feedback_text, edited_response)
    return True

async def mark_followup(
    pool: asyncpg.Pool,
    interaction_id: str
) -> bool:
    """Mark that a user asked a follow-up question (indicates incomplete answer)."""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE interaction_logs
            SET had_followup = TRUE
            WHERE id = $1
        """, interaction_id)
    return True
```

### Training Data Curation Service

```python
# services/curation.py
import json
import asyncpg
from datetime import datetime

async def get_curation_candidates(
    pool: asyncpg.Pool,
    limit: int = 50
) -> list[dict]:
    """
    Get interactions that are good candidates for training examples.
    Prioritizes: positive feedback, no follow-ups, user edits (corrected responses).
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id,
                system_prompt,
                user_message,
                assistant_response,
                user_edited_response,
                feedback_rating,
                feedback_text,
                had_followup,
                model_used,
                created_at
            FROM interaction_logs
            WHERE 
                -- Not already curated
                id NOT IN (SELECT source_interaction_id FROM training_examples WHERE source_interaction_id IS NOT NULL)
                -- Has some signal
                AND (
                    feedback_rating = 1  -- Thumbs up
                    OR user_edited_response IS NOT NULL  -- User corrected it
                )
                -- Exclude ones with follow-ups (likely incomplete)
                AND had_followup = FALSE
            ORDER BY 
                CASE WHEN user_edited_response IS NOT NULL THEN 0 ELSE 1 END,
                feedback_rating DESC,
                created_at DESC
            LIMIT $1
        """, limit)
    
    return [dict(row) for row in rows]

async def promote_to_training(
    pool: asyncpg.Pool,
    interaction_id: str,
    category: str,
    quality_score: int = 5,
    approved_by: str = None,
    custom_response: str = None  # Override the response if needed
) -> str:
    """Promote an interaction to a training example."""
    async with pool.acquire() as conn:
        # Get the interaction
        interaction = await conn.fetchrow("""
            SELECT system_prompt, user_message, assistant_response, user_edited_response
            FROM interaction_logs WHERE id = $1
        """, interaction_id)
        
        if not interaction:
            raise ValueError(f"Interaction {interaction_id} not found")
        
        # Use custom response, or user edit, or original
        final_response = (
            custom_response or 
            interaction['user_edited_response'] or 
            interaction['assistant_response']
        )
        
        # Insert training example
        row = await conn.fetchrow("""
            INSERT INTO training_examples (
                source_interaction_id,
                system_prompt,
                user_message,
                assistant_response,
                category,
                quality_score,
                is_approved,
                approved_by,
                approved_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            interaction_id,
            interaction['system_prompt'],
            interaction['user_message'],
            final_response,
            category,
            quality_score,
            approved_by is not None,
            approved_by,
            datetime.utcnow() if approved_by else None
        )
        
        return str(row['id'])

async def export_training_jsonl(
    pool: asyncpg.Pool,
    min_quality_score: int = 5,
    categories: list[str] = None
) -> str:
    """Export approved training examples as JSONL for fine-tuning."""
    async with pool.acquire() as conn:
        query = """
            SELECT system_prompt, user_message, assistant_response
            FROM training_examples
            WHERE is_approved = TRUE
            AND quality_score >= $1
        """
        params = [min_quality_score]
        
        if categories:
            query += " AND category = ANY($2)"
            params.append(categories)
        
        query += " ORDER BY quality_score DESC, created_at DESC"
        
        rows = await conn.fetch(query, *params)
    
    lines = []
    for row in rows:
        example = {
            "messages": [
                {"role": "system", "content": row['system_prompt']},
                {"role": "user", "content": row['user_message']},
                {"role": "assistant", "content": row['assistant_response']}
            ]
        }
        lines.append(json.dumps(example))
    
    return "\n".join(lines)
```

### Fine-Tuning Job Management

```python
# services/fine_tuning.py
import json
import tempfile
from datetime import datetime
from openai import OpenAI
import asyncpg
from config import config

client = OpenAI(api_key=config.openai_api_key)

async def create_fine_tuning_job(
    pool: asyncpg.Pool,
    base_model: str = "gpt-4o-mini-2024-07-18",
    min_quality_score: int = 6,
    categories: list[str] = None,
    n_epochs: int = 3,
    notes: str = None
) -> dict:
    """Create and submit a fine-tuning job to OpenAI."""
    from services.curation import export_training_jsonl
    
    # Export training data
    jsonl_content = await export_training_jsonl(
        pool, min_quality_score, categories
    )
    
    lines = jsonl_content.strip().split("\n")
    example_count = len(lines)
    
    if example_count < 10:
        raise ValueError(f"Need at least 10 examples, got {example_count}")
    
    # Upload file to OpenAI
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        
        with open(f.name, 'rb') as file:
            file_response = client.files.create(
                file=file,
                purpose="fine-tune"
            )
    
    # Create fine-tuning job
    job = client.fine_tuning.jobs.create(
        training_file=file_response.id,
        model=base_model,
        hyperparameters={
            "n_epochs": n_epochs
        }
    )
    
    # Get example IDs for tracking
    async with pool.acquire() as conn:
        example_ids = await conn.fetch("""
            SELECT id FROM training_examples
            WHERE is_approved = TRUE AND quality_score >= $1
        """, min_quality_score)
        example_ids = [row['id'] for row in example_ids]
    
    # Save job to database
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO fine_tuning_jobs (
                openai_job_id, openai_file_id, base_model,
                example_count, example_ids, status, notes, started_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """,
            job.id,
            file_response.id,
            base_model,
            example_count,
            example_ids,
            job.status,
            notes,
            datetime.utcnow()
        )
    
    return {
        "job_id": str(row['id']),
        "openai_job_id": job.id,
        "status": job.status,
        "example_count": example_count,
        "base_model": base_model
    }

async def check_job_status(
    pool: asyncpg.Pool,
    job_id: str
) -> dict:
    """Check and update the status of a fine-tuning job."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT openai_job_id, status FROM fine_tuning_jobs WHERE id = $1
        """, job_id)
    
    if not row:
        raise ValueError(f"Job {job_id} not found")
    
    # Get status from OpenAI
    job = client.fine_tuning.jobs.retrieve(row['openai_job_id'])
    
    # Update database
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE fine_tuning_jobs
            SET 
                status = $2,
                fine_tuned_model = $3,
                completed_at = CASE WHEN $2 IN ('succeeded', 'failed') THEN NOW() ELSE completed_at END,
                error_message = $4
            WHERE id = $1
        """,
            job_id,
            job.status,
            job.fine_tuned_model,
            job.error.message if job.error else None
        )
    
    return {
        "job_id": job_id,
        "status": job.status,
        "fine_tuned_model": job.fine_tuned_model,
        "error": job.error.message if job.error else None
    }

async def list_fine_tuned_models(pool: asyncpg.Pool) -> list[dict]:
    """List all successfully fine-tuned models."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id, fine_tuned_model, base_model, example_count,
                completed_at, notes
            FROM fine_tuning_jobs
            WHERE status = 'succeeded'
            ORDER BY completed_at DESC
        """)
    
    return [dict(row) for row in rows]
```

---

## 3. API Endpoints

```python
# api/routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import asyncpg

router = APIRouter()

# --- Chat ---

class ChatRequest(BaseModel):
    message: str
    session_id: str = None

class ChatResponse(BaseModel):
    response: str
    interaction_id: str
    sources_used: int
    model: str
    latency_ms: int

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, pool: asyncpg.Pool = Depends(get_pool)):
    from services.chat import chat_with_context
    result = await chat_with_context(
        user_message=request.message,
        pool=pool,
        session_id=request.session_id
    )
    return ChatResponse(**result)

# --- Feedback ---

class FeedbackRequest(BaseModel):
    interaction_id: str
    rating: int = None  # -1, 0, 1
    feedback_text: str = None
    edited_response: str = None

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest, pool: asyncpg.Pool = Depends(get_pool)):
    from services.feedback import record_feedback
    await record_feedback(
        pool=pool,
        interaction_id=request.interaction_id,
        rating=request.rating,
        feedback_text=request.feedback_text,
        edited_response=request.edited_response
    )
    return {"status": "ok"}

# --- Curation (Admin) ---

@router.get("/admin/curation/candidates")
async def get_candidates(limit: int = 50, pool: asyncpg.Pool = Depends(get_pool)):
    from services.curation import get_curation_candidates
    return await get_curation_candidates(pool, limit)

class PromoteRequest(BaseModel):
    interaction_id: str
    category: str
    quality_score: int = 5
    approved_by: str = None
    custom_response: str = None

@router.post("/admin/curation/promote")
async def promote(request: PromoteRequest, pool: asyncpg.Pool = Depends(get_pool)):
    from services.curation import promote_to_training
    example_id = await promote_to_training(
        pool=pool,
        interaction_id=request.interaction_id,
        category=request.category,
        quality_score=request.quality_score,
        approved_by=request.approved_by,
        custom_response=request.custom_response
    )
    return {"example_id": example_id}

@router.get("/admin/export/jsonl")
async def export_jsonl(
    min_quality: int = 5,
    pool: asyncpg.Pool = Depends(get_pool)
):
    from services.curation import export_training_jsonl
    jsonl = await export_training_jsonl(pool, min_quality)
    return {"jsonl": jsonl, "line_count": len(jsonl.strip().split("\n"))}

# --- Fine-Tuning (Admin) ---

class FineTuneRequest(BaseModel):
    base_model: str = "gpt-4o-mini-2024-07-18"
    min_quality_score: int = 6
    n_epochs: int = 3
    notes: str = None

@router.post("/admin/fine-tune/create")
async def create_job(request: FineTuneRequest, pool: asyncpg.Pool = Depends(get_pool)):
    from services.fine_tuning import create_fine_tuning_job
    return await create_fine_tuning_job(
        pool=pool,
        base_model=request.base_model,
        min_quality_score=request.min_quality_score,
        n_epochs=request.n_epochs,
        notes=request.notes
    )

@router.get("/admin/fine-tune/{job_id}/status")
async def job_status(job_id: str, pool: asyncpg.Pool = Depends(get_pool)):
    from services.fine_tuning import check_job_status
    return await check_job_status(pool, job_id)

@router.get("/admin/fine-tune/models")
async def list_models(pool: asyncpg.Pool = Depends(get_pool)):
    from services.fine_tuning import list_fine_tuned_models
    return await list_fine_tuned_models(pool)
```

---

## 4. Knowledge Base Population

```python
# scripts/populate_knowledge.py
"""
Script to populate the knowledge base with SEC filings, documentation, etc.
Run periodically or when new data is available.
"""

import asyncio
import asyncpg
from services.embeddings import get_embeddings_batch

async def add_documents(
    pool: asyncpg.Pool,
    documents: list[dict]
) -> int:
    """
    Add documents to the knowledge base.
    
    Each document should have:
    - title: str
    - content: str
    - source: str
    - source_ref: str (optional)
    - metadata: dict (optional)
    """
    # Batch embed all documents
    contents = [doc['content'] for doc in documents]
    embeddings = get_embeddings_batch(contents)
    
    async with pool.acquire() as conn:
        for doc, embedding in zip(documents, embeddings):
            await conn.execute("""
                INSERT INTO knowledge_documents 
                (title, content, source, source_ref, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING
            """,
                doc['title'],
                doc['content'],
                doc['source'],
                doc.get('source_ref'),
                embedding,
                doc.get('metadata', {})
            )
    
    return len(documents)

# Example usage for SEC filings
async def load_sec_filing(pool: asyncpg.Pool, ticker: str, filing_type: str, content: str):
    """Load a parsed SEC filing into the knowledge base."""
    # Split into chunks (adjust chunk size based on your needs)
    chunk_size = 1500  # tokens, roughly
    chunks = split_into_chunks(content, chunk_size)
    
    documents = [
        {
            "title": f"{ticker} {filing_type} - Section {i+1}",
            "content": chunk,
            "source": "sec_filing",
            "source_ref": f"{ticker}/{filing_type}",
            "metadata": {"ticker": ticker, "filing_type": filing_type, "chunk_index": i}
        }
        for i, chunk in enumerate(chunks)
    ]
    
    return await add_documents(pool, documents)

def split_into_chunks(text: str, max_tokens: int) -> list[str]:
    """Split text into chunks of approximately max_tokens."""
    # Simple word-based splitting (improve with tiktoken for accuracy)
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_tokens = len(word) // 4 + 1  # rough estimate
        if current_length + word_tokens > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = word_tokens
        else:
            current_chunk.append(word)
            current_length += word_tokens
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks
```

---

## 5. Environment Variables

```bash
# .env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# After first fine-tuning job succeeds, set this:
# FINE_TUNED_MODEL_ID=ft:gpt-4o-mini-2024-07-18:your-org::abc123
```

---

## Next Steps

1. Run the database migrations to create tables
2. Set up the API endpoints in your existing Railway backend
3. Populate the knowledge base with your SEC filing data
4. Start collecting interactions and feedback
5. After 50+ quality examples, run your first fine-tuning job
6. A/B test the fine-tuned model against base model

See `training-process.md` for the detailed training workflow.
