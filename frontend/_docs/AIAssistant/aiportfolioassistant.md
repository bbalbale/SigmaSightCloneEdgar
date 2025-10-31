# AI Portfolio Analysis Assistant - Architecture & Implementation Plan

**Last Updated**: October 18, 2025
**Status**: Planning Phase
**Owner**: Product & Engineering

---

## Executive Summary

Build a hybrid AI analysis system that provides institutional-quality portfolio commentary similar to what a senior analyst would deliver. The system will offer three modes of interaction:

1. **Automated Daily Insights**: Batch-generated commentary on portfolio changes
2. **On-Demand Deep Analysis**: User-triggered comprehensive analysis
3. **Chat Q&A**: Conversational analysis via existing chat interface

### Cost Economics at Scale

With intelligent caching and tiered optimization:

| User Base | Monthly LLM Cost | Notes |
|-----------|------------------|-------|
| **1,000 users** | **$1,360** | MVP scale, manageable (~$1.36/user) |
| **10,000 users** | **$8,160** | Need caching optimization |
| **100,000 users** | **$34,000** | Full optimization stack |

**Revenue Context**: At $20-50/user/month SaaS pricing, LLM costs represent **2-7% of revenue** - highly sustainable!

### Cost Per User Breakdown

**Assumptions**:
- Average user: 2 portfolios
- Active user rate: 50% (50% use advanced features monthly)
- Daily automated insights: 1 per portfolio (60×/month)
- On-demand analysis: 2× per month
- Chat sessions: 3× per month, 8 messages each

**Monthly Cost (per active user):**

| Feature | Frequency | Model | Input Tokens | Output Tokens | Cost |
|---------|-----------|-------|--------------|---------------|------|
| **Daily Insights** | 60×/mo | GPT-4o | 480K | 90K | **$2.10** |
| **Deep Analysis** | 2×/mo | Claude Sonnet | 30K | 6K | **$0.18** |
| **Chat Q&A** | 24 msgs/mo | GPT-4o | 96K | 19K | **$0.43** |
| | | | | **Total:** | **$2.71/mo** |

**Per user (all users, 50% active):** ~**$1.36/month**

### Cost Optimization Strategies

At 100K users, implement:

1. **Intelligent Caching** (saves ~60%)
   - Cache similar portfolio analyses for 24 hours
   - "HNW conservative" pattern → reuse insights with personalization
   - Brings 100K user cost to **~$80K/month**

2. **Tiered Analysis** (saves ~40%)
   - Free tier: Weekly insights only (not daily)
   - Pro tier: Daily insights + 5 deep analyses/month
   - Enterprise: Unlimited
   - Brings cost to **~$48K/month** for 100K users

3. **Smart Model Selection** (saves ~30%)
   - GPT-4o-mini for simple summaries ($0.15/$0.60 per 1M tokens)
   - GPT-4o for standard analysis
   - Claude Sonnet for complex reasoning
   - Brings cost to **~$34K/month** for 100K users

---

## Critical Distinction: Analytical Reasoning vs. Q&A Chat

### What Makes This Different From Existing Chat

**The Problem We're Solving:**

When you asked "why is the Hedge Fund portfolio volatility so high?", the value wasn't in fetching the data - it was in the **multi-step investigative reasoning process**:

1. Retrieved volatility: 18.61%
2. **Compared to benchmark**: "Is this normal for hedge funds?" → NO (should be 6-10%)
3. **Formed hypothesis**: "Maybe it's not actually hedged?"
4. **Tested hypothesis**: Calculated hedge ratio → 49.2% (confirmed!)
5. **Dug deeper**: "Why so low?" → Found concentrated tech longs + mismatched shorts
6. **Connected dots**: META 17.6% + MSFT 12.6% = 30% high-vol tech, but shorts in streaming/industrial
7. **Quantified gap**: $2M unhedged exposure
8. **Synthesized narrative**: "This isn't hedged - it's a leveraged tech bet"
9. **Gave specific fix**: "Add $1.6M in sector-matched shorts"

**This is investigative analysis, not data retrieval.**

### Two Complementary Systems

| System | Purpose | Trigger | Output | Model |
|--------|---------|---------|--------|-------|
| **Existing Chat** | Quick Q&A, data lookup | User asks question | Conversational answer | GPT-4o |
| **NEW Analytical Layer** | Multi-step investigation, root cause analysis | Nightly auto + on-demand | Structured insight | Claude Sonnet 4 |

**Examples:**

**Existing Chat (Keeps Doing):**
- "What's my largest position?" → "META at 17.6% ($717K)"
- "Show me tech holdings" → [List of tech positions]
- "What's my portfolio value?" → "$6.7M as of Oct 19"

**NEW Analytical Layer (New Capability):**
- **Nightly**: Auto-scans all metrics → Notices hedge ratio is 49% → Investigates why → Finds tech concentration + mismatched shorts → Generates insight: "Volatility Alert: Under-Hedged Tech Concentration"
- **On-Demand**: User clicks "Deep Analysis" on volatility → Multi-step investigation → "Your 18.6% vol is 2x expected because: (1) under-hedged, (2) concentrated tech, (3) asymmetric shorts"

### Free-Form AI Investigation Approach

**Not Rule-Based, Not Scripted - AI Decides What's Interesting:**

```python
system_prompt = """
You are a senior portfolio analyst conducting comprehensive portfolio review.

Your task:
1. SCAN all available metrics and identify anything noteworthy
2. INVESTIGATE root causes when you find anomalies
3. COMPARE to appropriate benchmarks for the strategy type
4. CONNECT disparate metrics to form hypotheses
5. SYNTHESIZE findings into actionable insights

Think like an analyst doing due diligence, not a chatbot answering questions.
"""
```

**Key Differentiator**: The AI explores the data to find problems, it doesn't just answer pre-defined questions.

### Handling Incomplete/Unreliable Calculation Data

**Current Reality**: Stress test, factor analysis, correlation scripts are still being debugged.

**How Analytical Layer Handles It:**

```markdown
# Example Nightly Insight

## Portfolio Risk Assessment

**Data Availability:**
- ✅ Volatility analysis: Complete (HAR model)
- ✅ Market beta: Complete
- ✅ Position data: Complete
- ⚠️ Stress tests: Incomplete (calculation debugging)
- ⚠️ Correlation matrix: Partial (15/30 pairs)

**Key Findings:**
1. **Under-Hedged Long/Short** (High Confidence)
   - Based on: Position-level data ✅
   - Hedge ratio: 49.2% vs target 90%+

2. **Stress Test Exposure** (Cannot Assess)
   - Data unavailable - rerun after debugging

**Note**: Analysis used 3 of 5 calculation modules.
```

**Value**: Get insights from what DOES work, while being transparent about limitations.

### Hybrid Data Access Strategy

**How Analytical Layer Gets Data:**

1. **Prefer batch calculation results** (stress, factor, beta, correlation)
   - Read from database tables populated by nightly scripts
   - Most efficient, already computed

2. **Fall back to API calls** when batch data missing
   - Call `/api/v1/data/portfolio/{id}/complete`
   - Get real-time position data

3. **Calculate on-demand** for analytical metrics
   - Hedge quality metrics
   - Volatility attribution
   - Concentration risk (HHI)
   - Strategy benchmark comparisons

**Example Flow:**
```python
async def build_investigation_context(portfolio_id):
    context = {
        'portfolio': await get_portfolio_data(portfolio_id),
        'positions': await get_positions(portfolio_id),
        'calculations': {}
    }

    # Try to get batch calculation results
    context['calculations']['volatility'] = await get_volatility_from_snapshot(portfolio_id)
    context['calculations']['stress_tests'] = await get_stress_results(portfolio_id)  # May be None
    context['calculations']['correlations'] = await get_correlations(portfolio_id)  # May be partial

    # Calculate analytical metrics on-demand
    context['analytics'] = {
        'hedge_quality': calculate_hedge_metrics(context['positions']),
        'concentration': calculate_hhi(context['positions']),
        'strategy_alignment': compare_to_benchmarks(context['portfolio'], context['calculations'])
    }

    return context
```

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
├─────────────────────────────────────────────────────────────┤
│  Dashboard Insights  │  Deep Analysis Page  │  Chat Interface│
└──────────┬──────────────────────┬──────────────────┬────────┘
           │                      │                  │
           ▼                      ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│  /api/v1/insights/daily/{id}                                │
│  /api/v1/analysis/deep (POST)                               │
│  /api/v1/chat/send (existing - enhanced with new tools)     │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│              AI Analysis Service Layer                       │
├─────────────────────────────────────────────────────────────┤
│  • Analysis Orchestrator                                     │
│  • Prompt Builder (Jinja2 templates)                        │
│  • Cache Manager (intelligent deduplication)                │
│  • Cost Tracker & Budget Controls                           │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                  LLM Provider Layer                          │
├─────────────────────────────────────────────────────────────┤
│  OpenAI Provider    │    Anthropic Provider                 │
│  (GPT-4o, 4o-mini)  │    (Claude Sonnet 4, Opus)           │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data & Storage Layer                        │
├─────────────────────────────────────────────────────────────┤
│  • ai_insights (generated analyses)                         │
│  • ai_insight_templates (prompt templates)                  │
│  • portfolio_snapshots (source data)                        │
│  • positions, market_data (context data)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Database Schema

### New Tables Required

```python
# app/models/ai_insights.py

class AIInsight(Base):
    """Stores AI-generated portfolio analysis and commentary"""
    __tablename__ = "ai_insights"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID, ForeignKey("portfolios.id"), nullable=False, index=True)

    # Classification
    insight_type = Column(Enum(
        "daily_summary",           # Brief daily update
        "volatility_analysis",     # Deep dive on volatility drivers
        "concentration_risk",      # Position/sector concentration
        "sector_drift",           # Portfolio drift from target allocation
        "attribution_analysis",   # Return attribution
        "custom"                  # Ad-hoc user request
    ), nullable=False)

    analysis_scope = Column(String)  # "portfolio", "position", "sector", "factor"

    # Content (structured for different UI presentations)
    title = Column(String(200))                    # "High Volatility Alert"
    summary = Column(Text)                         # 1-2 sentence TL;DR
    full_analysis = Column(Text)                   # Complete markdown analysis
    key_findings = Column(JSON)                    # ["Finding 1", "Finding 2"]
    recommendations = Column(JSON)                 # [{"action": "...", "impact": "..."}]
    severity = Column(String)                      # "info", "warning", "alert"

    # Metadata for tracking & optimization
    model_used = Column(String)                    # "gpt-4o", "claude-sonnet-4"
    prompt_version = Column(String)                # "volatility_v1.2"
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_usd = Column(Numeric(10, 6))             # Track actual cost
    generation_time_ms = Column(Integer)

    # Context snapshot (what data was analyzed)
    context_data = Column(JSON)                    # Portfolio metrics at analysis time
    referenced_date = Column(Date)                 # Date of snapshot analyzed

    # Caching & deduplication
    cache_key = Column(String, index=True)         # Hash of portfolio characteristics
    expires_at = Column(DateTime)                  # TTL for caching
    is_cached_variant = Column(Boolean, default=False)
    parent_insight_id = Column(UUID, ForeignKey("ai_insights.id"), nullable=True)

    # User interaction tracking
    viewed_at = Column(DateTime, nullable=True)
    user_rating = Column(Integer, nullable=True)   # 1-5 stars
    user_feedback = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="ai_insights")


class AIInsightTemplate(Base):
    """Reusable prompt templates for different analysis types"""
    __tablename__ = "ai_insight_templates"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True)  # "volatility_analysis_v1"
    display_name = Column(String)                    # "Volatility Deep Dive"
    description = Column(Text)
    insight_type = Column(String, nullable=False)

    # Prompt engineering
    system_prompt = Column(Text)                     # Role definition
    user_prompt_template = Column(Text)              # Jinja2 template with {{variables}}

    # Model configuration
    model_preference = Column(String, default="gpt-4o")  # "gpt-4o", "claude-sonnet"
    fallback_model = Column(String, default="gpt-4o-mini")
    max_tokens = Column(Integer, default=1500)
    temperature = Column(Float, default=0.7)

    # Required data for template rendering
    required_context = Column(JSON)  # ["volatility", "positions", "sector_weights"]

    # Version control
    version = Column(String, default="1.0")
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Performance tracking
    avg_quality_rating = Column(Float, nullable=True)
    usage_count = Column(Integer, default=0)
    avg_generation_time_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Migration Plan

```bash
# Create migration
alembic revision --autogenerate -m "Add AI insights and templates tables"

# Apply migration
alembic upgrade head

# Seed initial templates
python scripts/seed_ai_templates.py
```

---

## 2. Service Layer Architecture

### Directory Structure

```
app/services/ai_analysis/
├── __init__.py
├── analysis_service.py          # Main orchestrator
├── prompt_builder.py             # Template rendering with Jinja2
├── cache_manager.py              # Intelligent caching & deduplication
├── cost_tracker.py               # Budget monitoring & controls
├── context_builder.py            # Gather data for analysis
├── providers/
│   ├── __init__.py
│   ├── base_provider.py          # Abstract base class
│   ├── openai_provider.py        # GPT-4o integration
│   └── anthropic_provider.py     # Claude integration
└── templates/
    ├── volatility_analysis.j2
    ├── concentration_risk.j2
    ├── daily_summary.j2
    ├── sector_drift.j2
    └── attribution_analysis.j2
```

### Core Service Implementation

```python
# app/services/ai_analysis/analysis_service.py

from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
import hashlib
import json

from app.models.ai_insights import AIInsight, AIInsightTemplate
from app.models.snapshots import PortfolioSnapshot
from .prompt_builder import PromptBuilder
from .cache_manager import AnalysisCacheManager
from .cost_tracker import CostTracker
from .context_builder import ContextBuilder
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider


class AIAnalysisService:
    """
    Main service for generating AI-powered portfolio analysis.

    Handles orchestration of:
    - Context gathering from database
    - Prompt building from templates
    - LLM provider selection and execution
    - Caching and cost optimization
    - Result storage and retrieval
    """

    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.cache_manager = AnalysisCacheManager()
        self.cost_tracker = CostTracker()
        self.context_builder = ContextBuilder()

        # Initialize LLM providers
        self.providers = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider()
        }

    async def generate_insight(
        self,
        portfolio_id: UUID,
        insight_type: str,
        model: Optional[str] = None,
        depth: str = "standard",  # "quick", "standard", "deep"
        force_regenerate: bool = False,
        user_context: Optional[Dict[str, Any]] = None
    ) -> AIInsight:
        """
        Generate AI analysis for a portfolio.

        Args:
            portfolio_id: Portfolio to analyze
            insight_type: Type of analysis (volatility_analysis, concentration_risk, etc.)
            model: Override model selection (gpt-4o, claude-sonnet, etc.)
            depth: Analysis depth controlling context size and output length
            force_regenerate: Skip cache and generate fresh analysis
            user_context: Additional context from user (e.g., specific question)

        Returns:
            AIInsight object with generated analysis
        """

        # Check budget before generating
        if not await self.cost_tracker.check_budget(portfolio_id):
            raise BudgetExceededException("Monthly analysis budget exceeded")

        # Build context data needed for analysis
        context_data = await self.context_builder.build_context(
            portfolio_id=portfolio_id,
            insight_type=insight_type,
            depth=depth
        )

        # Generate cache key from portfolio characteristics
        cache_key = self._generate_cache_key(
            portfolio_id=portfolio_id,
            insight_type=insight_type,
            context_data=context_data
        )

        # Check cache unless force regeneration
        if not force_regenerate:
            cached_insight = await self.cache_manager.get_cached_insight(
                cache_key=cache_key,
                insight_type=insight_type,
                max_age_hours=self._get_cache_ttl(insight_type, depth)
            )

            if cached_insight:
                logger.info(f"Cache HIT: Saved ${cached_insight.cost_usd:.4f}")
                return cached_insight

        # Get prompt template for this insight type
        template = await self._get_template(insight_type, depth)

        # Select model (user override > template preference > default)
        selected_model = model or template.model_preference

        # Build prompt from template and context
        system_prompt, user_prompt = self.prompt_builder.build_prompts(
            template=template,
            context_data=context_data,
            user_context=user_context
        )

        # Select provider based on model
        provider = self._get_provider(selected_model)

        # Generate analysis
        start_time = datetime.utcnow()
        result = await provider.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=selected_model,
            max_tokens=template.max_tokens,
            temperature=template.temperature
        )
        generation_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Parse structured output from LLM
        parsed_content = self._parse_analysis_content(result["content"])

        # Calculate cost
        cost_usd = self._calculate_cost(
            model=selected_model,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"]
        )

        # Create AIInsight record
        insight = AIInsight(
            portfolio_id=portfolio_id,
            insight_type=insight_type,
            analysis_scope="portfolio",

            title=parsed_content["title"],
            summary=parsed_content["summary"],
            full_analysis=result["content"],
            key_findings=parsed_content["key_findings"],
            recommendations=parsed_content["recommendations"],
            severity=parsed_content.get("severity", "info"),

            model_used=selected_model,
            prompt_version=template.version,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            cost_usd=cost_usd,
            generation_time_ms=int(generation_time),

            context_data=context_data,
            referenced_date=context_data["snapshot_date"],

            cache_key=cache_key,
            expires_at=datetime.utcnow() + timedelta(hours=self._get_cache_ttl(insight_type, depth)),
            is_cached_variant=False
        )

        # Save to database
        async with get_async_session() as db:
            db.add(insight)
            await db.commit()
            await db.refresh(insight)

        # Track cost
        await self.cost_tracker.record_usage(
            portfolio_id=portfolio_id,
            cost_usd=cost_usd,
            insight_type=insight_type
        )

        logger.info(f"Generated {insight_type} analysis: ${cost_usd:.4f}, {generation_time:.0f}ms")

        return insight

    async def generate_daily_insights_batch(
        self,
        portfolio_ids: Optional[List[UUID]] = None
    ) -> List[AIInsight]:
        """
        Generate daily insights for multiple portfolios in batch.
        Called by nightly batch processing.

        Uses quick depth and aggressive caching to minimize costs.
        """

        if portfolio_ids is None:
            # Get all active portfolios
            async with get_async_session() as db:
                result = await db.execute(
                    select(Portfolio).where(Portfolio.deleted_at.is_(None))
                )
                portfolios = result.scalars().all()
                portfolio_ids = [p.id for p in portfolios]

        # Generate insights in parallel with concurrency limit
        insights = []
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent LLM calls

        async def generate_with_semaphore(portfolio_id):
            async with semaphore:
                return await self.generate_insight(
                    portfolio_id=portfolio_id,
                    insight_type="daily_summary",
                    depth="quick",
                    model="gpt-4o-mini"  # Cheapest for daily summaries
                )

        tasks = [generate_with_semaphore(pid) for pid in portfolio_ids]
        insights = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        successful = [i for i in insights if isinstance(i, AIInsight)]
        failed = [i for i in insights if isinstance(i, Exception)]

        if failed:
            logger.warning(f"Daily insights batch: {len(successful)} succeeded, {len(failed)} failed")

        return successful

    def _generate_cache_key(
        self,
        portfolio_id: UUID,
        insight_type: str,
        context_data: Dict[str, Any]
    ) -> str:
        """
        Generate cache key based on portfolio characteristics.

        Similar portfolios will generate the same cache key,
        allowing us to reuse analysis with minor personalization.
        """

        # Extract key characteristics that determine analysis content
        characteristics = {
            "insight_type": insight_type,
            "strategy_type": context_data.get("portfolio", {}).get("strategy_type"),
            "num_positions_bucket": self._bucket_position_count(
                context_data.get("portfolio", {}).get("num_positions", 0)
            ),
            "volatility_bucket": self._bucket_volatility(
                context_data.get("volatility", {}).get("realized_21d", 0)
            ),
            "total_value_bucket": self._bucket_portfolio_value(
                context_data.get("portfolio", {}).get("total_value", 0)
            ),
            # Include date for daily insights to ensure freshness
            "snapshot_date": context_data.get("snapshot_date").isoformat() if insight_type == "daily_summary" else None
        }

        # Create hash of characteristics
        characteristics_str = json.dumps(characteristics, sort_keys=True)
        cache_key = hashlib.sha256(characteristics_str.encode()).hexdigest()[:16]

        return f"{insight_type}:{cache_key}"

    def _bucket_position_count(self, count: int) -> str:
        """Bucket position counts for caching similarity"""
        if count < 10:
            return "small"
        elif count < 30:
            return "medium"
        else:
            return "large"

    def _bucket_volatility(self, vol: float) -> str:
        """Bucket volatility for caching similarity"""
        if vol < 0.10:
            return "low"
        elif vol < 0.20:
            return "moderate"
        else:
            return "high"

    def _bucket_portfolio_value(self, value: float) -> str:
        """Bucket portfolio size for caching similarity"""
        if value < 100000:
            return "retail"
        elif value < 1000000:
            return "affluent"
        elif value < 10000000:
            return "hnw"
        else:
            return "uhnw"

    def _get_cache_ttl(self, insight_type: str, depth: str) -> int:
        """Get cache TTL in hours based on insight type and depth"""
        ttls = {
            ("daily_summary", "quick"): 24,      # Daily insights expire daily
            ("volatility_analysis", "standard"): 6,  # Standard analyses expire in 6 hours
            ("volatility_analysis", "deep"): 1,      # Deep analyses expire in 1 hour (more personalized)
            ("concentration_risk", "standard"): 12,
            ("sector_drift", "standard"): 24,
        }
        return ttls.get((insight_type, depth), 6)  # Default 6 hours

    async def _get_template(
        self,
        insight_type: str,
        depth: str
    ) -> AIInsightTemplate:
        """Get prompt template for insight type"""

        async with get_async_session() as db:
            # Try to get depth-specific template first
            template_name = f"{insight_type}_{depth}"
            result = await db.execute(
                select(AIInsightTemplate).where(
                    AIInsightTemplate.name == template_name,
                    AIInsightTemplate.is_active == True
                )
            )
            template = result.scalar_one_or_none()

            # Fallback to default template for insight type
            if not template:
                result = await db.execute(
                    select(AIInsightTemplate).where(
                        AIInsightTemplate.insight_type == insight_type,
                        AIInsightTemplate.is_default == True,
                        AIInsightTemplate.is_active == True
                    )
                )
                template = result.scalar_one_or_none()

            if not template:
                raise TemplateNotFoundException(f"No template found for {insight_type}")

            return template

    def _get_provider(self, model: str):
        """Get LLM provider based on model name"""
        if "gpt" in model.lower() or "openai" in model.lower():
            return self.providers["openai"]
        elif "claude" in model.lower() or "anthropic" in model.lower():
            return self.providers["anthropic"]
        else:
            raise ValueError(f"Unknown model: {model}")

    def _parse_analysis_content(self, content: str) -> Dict[str, Any]:
        """
        Parse structured elements from LLM response.

        Expects markdown format with specific headers:
        # Title
        ## Summary
        ## Key Findings
        ## Recommendations
        """

        # Simple regex-based parsing (could use more sophisticated NLP)
        import re

        parsed = {
            "title": "",
            "summary": "",
            "key_findings": [],
            "recommendations": [],
            "severity": "info"
        }

        # Extract title (first # heading)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            parsed["title"] = title_match.group(1).strip()

        # Extract summary (content between ## Summary and next ##)
        summary_match = re.search(
            r'##\s+Summary\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if summary_match:
            parsed["summary"] = summary_match.group(1).strip()

        # Extract key findings (bullet points under ## Key Findings)
        findings_match = re.search(
            r'##\s+Key Findings\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if findings_match:
            findings_text = findings_match.group(1)
            parsed["key_findings"] = [
                line.strip('- •').strip()
                for line in findings_text.split('\n')
                if line.strip().startswith(('-', '•', '*'))
            ]

        # Extract recommendations
        recs_match = re.search(
            r'##\s+Recommendations\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if recs_match:
            recs_text = recs_match.group(1)
            parsed["recommendations"] = [
                line.strip('- •').strip()
                for line in recs_text.split('\n')
                if line.strip().startswith(('-', '•', '*'))
            ]

        # Detect severity from keywords
        content_lower = content.lower()
        if any(word in content_lower for word in ["alert", "critical", "urgent", "immediate"]):
            parsed["severity"] = "alert"
        elif any(word in content_lower for word in ["warning", "caution", "concern", "risk"]):
            parsed["severity"] = "warning"

        return parsed

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost in USD for LLM call"""

        # Pricing as of Oct 2025 (per 1M tokens)
        pricing = {
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "claude-sonnet-4": {"input": 3.00, "output": 15.00},
            "claude-opus-4": {"input": 15.00, "output": 75.00},
        }

        if model not in pricing:
            logger.warning(f"Unknown model for cost calculation: {model}")
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing[model]["input"]
        output_cost = (output_tokens / 1_000_000) * pricing[model]["output"]

        return input_cost + output_cost


# Singleton instance
ai_analysis_service = AIAnalysisService()
```

---

## 3. Prompt Engineering Templates

### Volatility Analysis Template

```jinja2
{# templates/volatility_analysis.j2 #}

{# SYSTEM PROMPT #}
You are a senior portfolio risk analyst with deep expertise in volatility analysis and portfolio construction. Your role is to provide insightful, actionable analysis of portfolio volatility patterns.

Focus on:
1. Root cause identification (not just symptoms)
2. Comparison to appropriate benchmarks
3. Actionable recommendations
4. Clear explanations accessible to sophisticated investors

Be specific with numbers and percentages. Cite exact positions and exposures. Structure your response with these sections:

# [Concise Title]

## Summary
[1-2 sentence TL;DR of volatility assessment]

## Key Findings
- [Finding 1 with specific data]
- [Finding 2 with specific data]
- [Finding 3 with specific data]

## Analysis
[Detailed explanation of volatility drivers]

## Recommendations
- [Specific actionable recommendation 1]
- [Specific actionable recommendation 2]


{# USER PROMPT #}
Analyze the volatility characteristics of this portfolio:

## Portfolio Overview
- Name: {{ portfolio.name }}
- Strategy: {{ portfolio.strategy_type }}
- Total Value: ${{ portfolio.total_value | format_currency }}
- Position Count: {{ portfolio.num_positions }}
{% if portfolio.description -%}
- Description: {{ portfolio.description }}
{% endif %}

## Volatility Metrics
- 21-Day Realized Volatility: {{ (volatility.realized_21d * 100) | round(2) }}%
- 63-Day Realized Volatility: {{ (volatility.realized_63d * 100) | round(2) }}%
- Expected Volatility (HAR): {{ (volatility.expected * 100) | round(2) }}%
- Trend: {{ volatility.trend }}
{% if volatility.percentile -%}
- Percentile (vs 1-year history): {{ (volatility.percentile * 100) | round(1) }}th
{% endif %}

## Position Breakdown (Top 10)
{% for position in top_10_positions -%}
- **{{ position.symbol }}**: {{ position.position_type }} | ${{ position.market_value | format_currency }} ({{ (position.weight * 100) | round(1) }}%) | {{ position.investment_class }}
{% endfor %}

## Exposure Analysis
- Long Exposure: ${{ exposures.long_value | format_currency }}
- Short Exposure: ${{ exposures.short_value | format_currency }}
- Net Exposure: ${{ exposures.net_exposure | format_currency }}
{% if exposures.long_value > 0 -%}
- Hedge Ratio: {{ (exposures.short_value / exposures.long_value * 100) | round(1) }}%
{% endif %}

## Sector Concentration
{% for sector, weight in sector_weights.items() -%}
- {{ sector }}: {{ (weight * 100) | round(1) }}%
{% endfor %}

{% if user_question -%}
## User Question
{{ user_question }}
{% endif %}

Please provide:
1. **Volatility Assessment**: Is this volatility appropriate for the strategy? Why/why not?
2. **Key Drivers**: What specific positions or exposures are driving volatility?
3. **Comparison to Expectations**: For a {{ portfolio.strategy_type }} strategy, what would be typical volatility?
4. **Recommendations**: Specific actionable steps to adjust volatility if needed

Be direct and specific. Use exact numbers from the data above.
```

### Daily Summary Template

```jinja2
{# templates/daily_summary.j2 #}

{# SYSTEM PROMPT #}
You are a portfolio analyst providing concise daily summaries for busy investors. Your summaries should be:
- Brief (2-3 sentences max)
- Highlight the most important change or observation
- Include specific numbers
- End with a clear takeaway

Format as plain text, no markdown.

{# USER PROMPT #}
Summarize the key insight for this portfolio today:

Portfolio: {{ portfolio.name }}
Value: ${{ portfolio.total_value | format_currency }} ({{ change_pct }}% {{ change_direction }})
Key Position Change: {{ top_mover.symbol }} {{ top_mover.direction }} {{ (top_mover.change_pct * 100) | round(1) }}%

{% if volatility.realized_21d > 0.15 -%}
Note: Volatility is elevated at {{ (volatility.realized_21d * 100) | round(1) }}%.
{% endif %}

Provide a 2-3 sentence summary highlighting the most important observation for today.
```

### Concentration Risk Template

```jinja2
{# templates/concentration_risk.j2 #}

{# SYSTEM PROMPT #}
You are a portfolio risk manager specializing in concentration risk assessment. Identify:
1. Single position concentration (>10% flags)
2. Sector/factor concentration (>25% flags)
3. Correlation amplification (concentrated positions that move together)
4. Specific recommendations to reduce concentration

Be quantitative and specific. Structure your response with clear sections.

{# USER PROMPT #}
Analyze concentration risk in this portfolio:

## Portfolio Overview
- Name: {{ portfolio.name }}
- Total Value: ${{ portfolio.total_value | format_currency }}
- Number of Positions: {{ portfolio.num_positions }}

## Position Concentration
Top 5 Positions ({{ (top_5_total_weight * 100) | round(1) }}% of portfolio):
{% for pos in top_5_positions -%}
- **{{ pos.symbol }}**: ${{ pos.market_value | format_currency }} ({{ (pos.weight * 100) | round(1) }}%)
{% endfor %}

{% if max_position_weight > 0.10 -%}
⚠️ Position exceeding 10% threshold detected
{% endif %}

## Sector Concentration
{% for sector, data in sectors.items() -%}
- **{{ sector }}**: {{ (data.weight * 100) | round(1) }}% ({{ data.position_count }} positions)
{% endfor %}

{% set max_sector_weight = sectors.values() | map(attribute='weight') | max -%}
{% if max_sector_weight > 0.25 -%}
⚠️ Sector exceeding 25% threshold detected
{% endif %}

## Investment Class Breakdown
{% for iclass, data in investment_classes.items() -%}
- **{{ iclass }}**: {{ (data.weight * 100) | round(1) }}% ({{ data.position_count }} positions)
{% endfor %}

Please analyze:
1. **Single Position Risk**: Flag any concerning concentrations
2. **Sector Concentration**: Assess sector diversification
3. **Correlation Risk**: Are concentrated positions correlated?
4. **Recommendations**: Specific actions to reduce concentration

Provide specific position names and target allocation percentages.
```

---

## 4. Integration Points

### A. Batch Processing Integration

```python
# app/batch/jobs/ai_insights_generator.py

from app.services.ai_analysis.analysis_service import ai_analysis_service

async def generate_daily_insights_job():
    """
    Batch job to generate AI insights for all portfolios.
    Called after nightly portfolio snapshot creation.
    """

    logger.info("Starting daily AI insights generation")

    # Generate insights for all active portfolios
    insights = await ai_analysis_service.generate_daily_insights_batch()

    logger.info(f"Generated {len(insights)} daily insights")

    # Optional: Send email digest to users with new insights
    await send_insight_digest_emails(insights)

    return {"insights_generated": len(insights)}


# Add to batch orchestrator
# app/batch/batch_orchestrator_v2.py

async def run_daily_batch_sequence(self, portfolio_id: Optional[UUID] = None):
    """Run the complete daily batch sequence"""

    # ... existing batch jobs ...

    # Phase 9: Generate AI Insights (runs after snapshots created)
    await self._generate_ai_insights(portfolio_id)

    logger.info("✅ Daily batch sequence completed")


async def _generate_ai_insights(self, portfolio_id: Optional[UUID] = None):
    """Generate AI insights for portfolios"""

    try:
        if portfolio_id:
            # Single portfolio
            await ai_analysis_service.generate_insight(
                portfolio_id=portfolio_id,
                insight_type="daily_summary",
                depth="quick"
            )
        else:
            # All portfolios
            await generate_daily_insights_job()

    except Exception as e:
        logger.error(f"AI insights generation failed: {e}")
        # Don't fail entire batch if AI insights fail
```

### B. REST API Endpoints

```python
# app/api/v1/insights.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.core.dependencies import get_current_user
from app.models.users import User
from app.models.ai_insights import AIInsight
from app.services.ai_analysis.analysis_service import ai_analysis_service
from app.database import get_async_session

router = APIRouter(prefix="/insights", tags=["AI Insights"])


@router.get("/daily/{portfolio_id}")
async def get_daily_insights(
    portfolio_id: UUID,
    limit: int = Query(7, ge=1, le=30),  # Default last 7 days
    current_user: User = Depends(get_current_user)
):
    """
    Get daily insights for a portfolio.
    Returns recent daily summaries.
    """

    # Verify user has access to portfolio
    await verify_portfolio_access(current_user.id, portfolio_id)

    async with get_async_session() as db:
        result = await db.execute(
            select(AIInsight)
            .where(
                AIInsight.portfolio_id == portfolio_id,
                AIInsight.insight_type == "daily_summary"
            )
            .order_by(AIInsight.created_at.desc())
            .limit(limit)
        )
        insights = result.scalars().all()

    return {
        "portfolio_id": str(portfolio_id),
        "insights": [
            {
                "id": str(insight.id),
                "title": insight.title,
                "summary": insight.summary,
                "severity": insight.severity,
                "referenced_date": insight.referenced_date.isoformat(),
                "created_at": insight.created_at.isoformat()
            }
            for insight in insights
        ]
    }


@router.get("/latest/{portfolio_id}")
async def get_latest_insight(
    portfolio_id: UUID,
    insight_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get the most recent insight for a portfolio.
    Optionally filter by insight_type.
    """

    await verify_portfolio_access(current_user.id, portfolio_id)

    async with get_async_session() as db:
        query = select(AIInsight).where(
            AIInsight.portfolio_id == portfolio_id
        )

        if insight_type:
            query = query.where(AIInsight.insight_type == insight_type)

        query = query.order_by(AIInsight.created_at.desc()).limit(1)

        result = await db.execute(query)
        insight = result.scalar_one_or_none()

    if not insight:
        raise HTTPException(status_code=404, detail="No insights found")

    return {
        "id": str(insight.id),
        "portfolio_id": str(insight.portfolio_id),
        "insight_type": insight.insight_type,
        "title": insight.title,
        "summary": insight.summary,
        "full_analysis": insight.full_analysis,
        "key_findings": insight.key_findings,
        "recommendations": insight.recommendations,
        "severity": insight.severity,
        "referenced_date": insight.referenced_date.isoformat(),
        "created_at": insight.created_at.isoformat(),
        "model_used": insight.model_used,
        "generation_time_ms": insight.generation_time_ms
    }


@router.post("/analyze")
async def generate_on_demand_analysis(
    portfolio_id: UUID,
    insight_type: str = Query(..., description="Type of analysis to generate"),
    model: Optional[str] = Query(None, description="Override model (gpt-4o, claude-sonnet)"),
    depth: str = Query("standard", description="Analysis depth (quick, standard, deep)"),
    user_question: Optional[str] = Query(None, description="Custom question for analysis"),
    current_user: User = Depends(get_current_user)
):
    """
    Generate on-demand deep analysis for a portfolio.

    This endpoint triggers fresh analysis generation and may take several seconds.
    Uses Claude for deep analysis to maximize quality.
    """

    await verify_portfolio_access(current_user.id, portfolio_id)

    # Validate insight_type
    valid_types = ["volatility_analysis", "concentration_risk", "sector_drift", "attribution_analysis"]
    if insight_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid insight_type. Must be one of: {', '.join(valid_types)}"
        )

    # Generate analysis (checks budget limits internally)
    try:
        user_context = {"user_question": user_question} if user_question else None

        insight = await ai_analysis_service.generate_insight(
            portfolio_id=portfolio_id,
            insight_type=insight_type,
            model=model,
            depth=depth,
            force_regenerate=False,  # Allow caching
            user_context=user_context
        )

        return {
            "id": str(insight.id),
            "portfolio_id": str(insight.portfolio_id),
            "insight_type": insight.insight_type,
            "title": insight.title,
            "summary": insight.summary,
            "full_analysis": insight.full_analysis,
            "key_findings": insight.key_findings,
            "recommendations": insight.recommendations,
            "severity": insight.severity,
            "referenced_date": insight.referenced_date.isoformat(),
            "created_at": insight.created_at.isoformat(),
            "model_used": insight.model_used,
            "cost_usd": float(insight.cost_usd),
            "generation_time_ms": insight.generation_time_ms,
            "is_cached": False
        }

    except BudgetExceededException as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.error(f"On-demand analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Analysis generation failed")


@router.get("/history/{portfolio_id}")
async def get_insight_history(
    portfolio_id: UUID,
    insight_type: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical insights for a portfolio.
    Useful for tracking how analysis has evolved over time.
    """

    await verify_portfolio_access(current_user.id, portfolio_id)

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    async with get_async_session() as db:
        query = select(AIInsight).where(
            AIInsight.portfolio_id == portfolio_id,
            AIInsight.created_at >= cutoff_date
        )

        if insight_type:
            query = query.where(AIInsight.insight_type == insight_type)

        query = query.order_by(AIInsight.created_at.desc())

        result = await db.execute(query)
        insights = result.scalars().all()

    return {
        "portfolio_id": str(portfolio_id),
        "period_days": days,
        "count": len(insights),
        "insights": [
            {
                "id": str(insight.id),
                "insight_type": insight.insight_type,
                "title": insight.title,
                "summary": insight.summary,
                "severity": insight.severity,
                "referenced_date": insight.referenced_date.isoformat(),
                "created_at": insight.created_at.isoformat(),
                "model_used": insight.model_used
            }
            for insight in insights
        ]
    }


@router.post("/{insight_id}/feedback")
async def submit_insight_feedback(
    insight_id: UUID,
    rating: int = Query(..., ge=1, le=5),
    feedback: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Submit user feedback on an insight.
    Used to improve prompt quality over time.
    """

    async with get_async_session() as db:
        result = await db.execute(
            select(AIInsight).where(AIInsight.id == insight_id)
        )
        insight = result.scalar_one_or_none()

        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")

        # Verify user has access to this portfolio
        await verify_portfolio_access(current_user.id, insight.portfolio_id)

        # Update feedback
        insight.user_rating = rating
        insight.user_feedback = feedback
        insight.viewed_at = datetime.utcnow()

        await db.commit()

    return {"status": "success", "message": "Feedback recorded"}


# Add to main router
# app/api/v1/router.py
from app.api.v1.insights import router as insights_router

api_router.include_router(insights_router)
```

### C. Chat Integration (Enhanced Tools)

```python
# app/agent/tools/portfolio_analysis_tools.py

from app.agent.tools.tool_registry import tool_registry
from app.services.ai_analysis.analysis_service import ai_analysis_service

@tool_registry.register("analyze_portfolio_insight")
async def analyze_portfolio_insight(
    portfolio_id: str,
    question: str,
    context: dict
) -> dict:
    """
    Generate contextual AI analysis based on user question.

    This tool is called by the chat system when users ask analytical questions
    like "Why is my volatility so high?" or "Is my portfolio well-hedged?"

    Args:
        portfolio_id: Portfolio UUID
        question: User's question
        context: Additional context from chat system

    Returns:
        dict with analysis results
    """

    try:
        # Generate custom insight based on user question
        insight = await ai_analysis_service.generate_insight(
            portfolio_id=UUID(portfolio_id),
            insight_type="custom",
            depth="standard",
            model="gpt-4o",  # Use GPT-4o for chat (faster than Claude)
            user_context={"user_question": question}
        )

        return {
            "success": True,
            "data": {
                "title": insight.title,
                "analysis": insight.full_analysis,
                "key_findings": insight.key_findings,
                "recommendations": insight.recommendations,
                "model_used": insight.model_used,
                "generation_time_ms": insight.generation_time_ms
            }
        }

    except Exception as e:
        logger.error(f"Chat analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool_registry.register("get_latest_insight")
async def get_latest_insight(
    portfolio_id: str,
    insight_type: Optional[str] = None,
    context: dict = None
) -> dict:
    """
    Retrieve the most recent AI-generated insight for a portfolio.

    Used by chat to quickly reference existing analysis without regenerating.
    """

    try:
        async with get_async_session() as db:
            query = select(AIInsight).where(
                AIInsight.portfolio_id == UUID(portfolio_id)
            )

            if insight_type:
                query = query.where(AIInsight.insight_type == insight_type)

            query = query.order_by(AIInsight.created_at.desc()).limit(1)

            result = await db.execute(query)
            insight = result.scalar_one_or_none()

        if not insight:
            return {
                "success": False,
                "error": "No recent insights found"
            }

        return {
            "success": True,
            "data": {
                "title": insight.title,
                "summary": insight.summary,
                "analysis": insight.full_analysis,
                "key_findings": insight.key_findings,
                "recommendations": insight.recommendations,
                "severity": insight.severity,
                "created_at": insight.created_at.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to retrieve insight: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

---

## 5. Caching & Cost Optimization

### 5.1 Portfolio Similarity Matching Algorithm - Deep Dive

The caching system needs to answer: **"Have we analyzed a portfolio similar enough to this one that we can reuse the analysis?"**

This is the most technically complex piece and drives our 60% cost reduction claim that makes the economics work at scale.

#### The Bucketing Algorithm

The key insight is that portfolios don't need to be *identical* to have similar analysis - they need similar *characteristics*. We bucket portfolios into discrete ranges to maximize cache reuse.

```python
# app/services/ai_analysis/similarity_matcher.py

from dataclasses import dataclass
from typing import Dict, Optional
from decimal import Decimal

@dataclass
class PortfolioCharacteristics:
    """Normalized portfolio characteristics for cache matching"""

    # Portfolio composition
    position_count_bucket: str  # "small" (<10), "medium" (10-30), "large" (>30)
    asset_class_mix: str        # "equity_only", "multi_asset", "options_heavy"

    # Risk profile
    volatility_bucket: str      # "low" (<10%), "moderate" (10-20%), "high" (>20%)
    concentration_level: str    # "diversified", "moderate", "concentrated"

    # Size/strategy
    total_value_bucket: str     # "retail" (<100K), "affluent" (100K-1M), "hnw" (1M-10M), "uhnw" (>10M)
    strategy_type: str          # "long_only", "long_short", "balanced", "growth", "income"

    # For long/short portfolios
    hedge_ratio_bucket: Optional[str]  # "market_neutral" (>90%), "partial" (50-90%), "minimal" (<50%)

    # Sector exposure
    sector_concentration: str   # "diversified", "tech_heavy", "finance_heavy", etc.

def calculate_portfolio_characteristics(
    portfolio_data: Dict,
    snapshot_data: Dict
) -> PortfolioCharacteristics:
    """
    Extract bucketed characteristics from portfolio data.
    Uses ranges instead of exact values for cache matching.
    """

    # Position count bucketing
    num_positions = len(portfolio_data['positions'])
    if num_positions < 10:
        position_bucket = "small"
    elif num_positions <= 30:
        position_bucket = "medium"
    else:
        position_bucket = "large"

    # Volatility bucketing (from snapshot)
    volatility = snapshot_data.get('realized_volatility_21d', 0)
    if volatility < 0.10:
        vol_bucket = "low"
    elif volatility <= 0.20:
        vol_bucket = "moderate"
    else:
        vol_bucket = "high"

    # Concentration analysis (HHI - Herfindahl-Hirschman Index)
    position_weights = [p['market_value'] / snapshot_data['total_value']
                       for p in portfolio_data['positions']]
    hhi = sum(w**2 for w in position_weights)

    if hhi < 0.10:
        concentration = "diversified"
    elif hhi < 0.25:
        concentration = "moderate"
    else:
        concentration = "concentrated"

    # Asset class mix
    option_pct = sum(1 for p in portfolio_data['positions']
                     if p['investment_class'] == 'OPTION') / num_positions

    if option_pct > 0.25:
        asset_mix = "options_heavy"
    elif any(p['investment_class'] == 'PRIVATE' for p in portfolio_data['positions']):
        asset_mix = "multi_asset"
    else:
        asset_mix = "equity_only"

    # Strategy type detection
    long_value = sum(p['market_value'] for p in portfolio_data['positions']
                     if p['position_type'] == 'LONG')
    short_value = abs(sum(p['market_value'] for p in portfolio_data['positions']
                          if p['position_type'] == 'SHORT'))

    if short_value == 0:
        strategy = "long_only"
        hedge_bucket = None
    else:
        hedge_ratio = short_value / long_value if long_value > 0 else 0
        if hedge_ratio > 0.90:
            strategy = "market_neutral"
            hedge_bucket = "market_neutral"
        elif hedge_ratio > 0.50:
            strategy = "long_short"
            hedge_bucket = "partial"
        else:
            strategy = "long_short"
            hedge_bucket = "minimal"

    # Sector concentration
    sector_weights = {}
    for pos in portfolio_data['positions']:
        sector = pos.get('sector', 'Unknown')
        weight = pos['market_value'] / snapshot_data['total_value']
        sector_weights[sector] = sector_weights.get(sector, 0) + weight

    if sector_weights:
        max_sector = max(sector_weights.items(), key=lambda x: x[1])
        if max_sector[1] > 0.50:
            sector_conc = f"{max_sector[0].lower()}_heavy"
        else:
            sector_conc = "diversified"
    else:
        sector_conc = "diversified"

    return PortfolioCharacteristics(
        position_count_bucket=position_bucket,
        asset_class_mix=asset_mix,
        volatility_bucket=vol_bucket,
        concentration_level=concentration,
        total_value_bucket=_get_value_bucket(snapshot_data['total_value']),
        strategy_type=strategy,
        hedge_ratio_bucket=hedge_bucket,
        sector_concentration=sector_conc
    )

def _get_value_bucket(total_value: float) -> str:
    """Bucket portfolio total value for similarity matching"""
    if total_value < 100_000:
        return "retail"
    elif total_value < 1_000_000:
        return "affluent"
    elif total_value < 10_000_000:
        return "hnw"
    else:
        return "uhnw"
```

#### Cache Key Generation

Different insight types focus on different characteristics:

```python
def generate_cache_key(
    insight_type: str,
    characteristics: PortfolioCharacteristics
) -> str:
    """
    Generate deterministic cache key from portfolio characteristics.

    Different insight types focus on different characteristics:
    - Volatility analysis: vol_bucket, strategy, hedge_ratio
    - Concentration risk: concentration, sector, position_count
    - Daily summary: all characteristics (broader match)
    """

    if insight_type == "volatility_analysis":
        # Focus on risk-related characteristics
        key_components = [
            insight_type,
            characteristics.volatility_bucket,
            characteristics.strategy_type,
            characteristics.hedge_ratio_bucket or "none",
            characteristics.asset_class_mix
        ]

    elif insight_type == "concentration_risk":
        # Focus on diversification characteristics
        key_components = [
            insight_type,
            characteristics.concentration_level,
            characteristics.sector_concentration,
            characteristics.position_count_bucket
        ]

    elif insight_type == "daily_summary":
        # Broader match - use most characteristics
        key_components = [
            insight_type,
            characteristics.strategy_type,
            characteristics.volatility_bucket,
            characteristics.concentration_level,
            characteristics.total_value_bucket
        ]

    else:
        # Custom analysis - use all characteristics
        key_components = [
            insight_type,
            characteristics.strategy_type,
            characteristics.volatility_bucket,
            characteristics.concentration_level,
            characteristics.position_count_bucket,
            characteristics.sector_concentration
        ]

    # Create hash
    import hashlib
    key_string = "|".join(str(c) for c in key_components)
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]
```

#### The Personalization Layer

**Critical**: Even with a cache hit, we customize the output to make it feel personalized and accurate.

```python
async def personalize_cached_insight(
    cached_insight: AIInsight,
    portfolio_id: UUID,
    current_data: Dict
) -> AIInsight:
    """
    Take cached generic analysis and personalize it with actual portfolio data.

    Example transformations:
    Cached: "Your portfolio's 18.5% volatility is 120% higher than expected..."
    Personalized: "Your portfolio's 18.61% volatility is 125% higher than expected..."

    Cached: "Top tech concentration (META 17.5%)"
    Personalized: "Top tech concentration (META 17.6%, MSFT 12.6%, GOOGL 11.2%)"
    """

    # Clone the cached insight
    new_insight = AIInsight(
        id=uuid4(),
        portfolio_id=portfolio_id,
        insight_type=cached_insight.insight_type,
        model_used=cached_insight.model_used + "_cached",
        cost_usd=Decimal("0.0001"),  # Minimal cost for personalization
        cache_hit=True,
        cache_source_id=cached_insight.id
    )

    # Personalize title
    new_insight.title = cached_insight.title.replace(
        "Your portfolio",
        f"{current_data['portfolio_name']}"
    )

    # Personalize summary with exact values
    summary = cached_insight.summary

    # Replace bucketed volatility with exact value
    exact_vol = current_data['snapshot']['realized_volatility_21d']
    summary = re.sub(
        r'\d+\.?\d*%\s+volatility',
        f'{exact_vol * 100:.2f}% volatility',
        summary
    )

    # Replace generic position names with actual top positions
    if 'top_positions' in current_data:
        top_3 = current_data['top_positions'][:3]
        position_string = ", ".join([f"{p['symbol']} {p['weight']*100:.1f}%"
                                     for p in top_3])
        # Find and replace generic position mentions
        summary = re.sub(
            r'top positions \([^)]+\)',
            f'top positions ({position_string})',
            summary,
            flags=re.IGNORECASE
        )

    new_insight.summary = summary

    # Similarly personalize full_analysis, key_findings, recommendations
    new_insight.full_analysis = _personalize_analysis_text(
        cached_insight.full_analysis,
        current_data
    )

    new_insight.key_findings = _personalize_findings(
        cached_insight.key_findings,
        current_data
    )

    new_insight.recommendations = _personalize_recommendations(
        cached_insight.recommendations,
        current_data
    )

    return new_insight

def _personalize_analysis_text(cached_text: str, current_data: Dict) -> str:
    """Replace generic values with portfolio-specific exact values"""
    text = cached_text

    # Replace portfolio name
    text = text.replace("Your portfolio", current_data['portfolio_name'])

    # Replace exact volatility values
    if 'realized_volatility_21d' in current_data['snapshot']:
        vol = current_data['snapshot']['realized_volatility_21d']
        # Find and replace volatility mentions (e.g., "18.5%" → "18.61%")
        text = re.sub(
            r'\b\d+\.?\d*%\s+volatility',
            f'{vol * 100:.2f}% volatility',
            text
        )

    # Replace position symbols and weights
    if 'top_positions' in current_data:
        for i, pos in enumerate(current_data['top_positions'][:5], 1):
            # Replace placeholder positions with actual
            text = re.sub(
                rf'\b(Position|Stock)\s*{i}\b',
                pos['symbol'],
                text,
                flags=re.IGNORECASE
            )

    return text

def _personalize_findings(cached_findings: List[str], current_data: Dict) -> List[str]:
    """Personalize each key finding with exact data"""
    personalized = []
    for finding in cached_findings:
        personalized_finding = finding

        # Replace exact values
        if 'hedge_ratio' in current_data:
            personalized_finding = re.sub(
                r'\d+\.?\d*%\s+hedge\s+ratio',
                f"{current_data['hedge_ratio'] * 100:.1f}% hedge ratio",
                personalized_finding
            )

        personalized.append(personalized_finding)

    return personalized

def _personalize_recommendations(cached_recs: List[str], current_data: Dict) -> List[str]:
    """Personalize recommendations with specific position names and values"""
    personalized = []
    for rec in cached_recs:
        personalized_rec = rec

        # Replace generic "largest position" with actual symbol
        if 'top_positions' in current_data and current_data['top_positions']:
            largest = current_data['top_positions'][0]
            personalized_rec = personalized_rec.replace(
                "largest position",
                f"{largest['symbol']}"
            )

        personalized.append(personalized_rec)

    return personalized
```

#### Expected Cache Hit Rates

Based on the bucketing strategy, here's what we expect in practice:

**High Hit Rate Scenarios (70-80%)**:
- Daily summaries for retail portfolios (most portfolios are similar)
- Standard volatility analyses for long-only equity portfolios
- Concentration risk for 10-30 position portfolios

**Medium Hit Rate Scenarios (50-60%)**:
- Deep analyses (more specific to portfolio details)
- Long/short portfolios (more variation in hedge ratios)
- Multi-asset portfolios (more complex characteristics)

**Low Hit Rate Scenarios (20-30%)**:
- Custom user-requested analyses
- Unusual portfolio structures (e.g., 100% options)
- First-time analysis types (cache not yet populated)

**Overall Target: 60% weighted average** across all insight types and user base.

#### Cache Invalidation Rules

```python
# Cache entries should be invalidated when:

1. **Time-based**:
   - Daily summaries: 24 hours
   - Volatility analyses: 7 days (vol changes slowly)
   - Concentration risk: 30 days (positions change less frequently)

2. **Data-driven**:
   - Portfolio characteristics shift buckets
     (e.g., volatility goes from "moderate" to "high")
   - Strategy type changes (e.g., adds short positions)
   - Major composition change (>25% of positions changed)

3. **Model updates**:
   - Prompt template version changes
   - LLM model upgrade
   - Analysis logic improvements

async def should_invalidate_cache(
    cached_insight: AIInsight,
    current_characteristics: PortfolioCharacteristics
) -> bool:
    """
    Determine if cached insight should be invalidated despite matching cache key.

    Returns True if cache should be invalidated and fresh analysis generated.
    """

    # Check time-based expiration
    if cached_insight.expires_at and cached_insight.expires_at < datetime.utcnow():
        return True

    # Check if prompt template version changed
    current_template = await get_template(cached_insight.insight_type)
    if current_template.version != cached_insight.prompt_version:
        return True

    # For daily summaries, always regenerate if more than 24 hours old
    if cached_insight.insight_type == "daily_summary":
        age_hours = (datetime.utcnow() - cached_insight.created_at).total_seconds() / 3600
        if age_hours > 24:
            return True

    # Check if portfolio characteristics changed significantly
    # (even within same bucket, extreme changes should trigger fresh analysis)
    if cached_insight.context_data:
        old_vol = cached_insight.context_data.get('volatility', {}).get('realized_21d', 0)
        new_vol = current_characteristics.volatility_bucket

        # If volatility changed by >50% even within same bucket, regenerate
        if abs(old_vol - new_vol) > 0.5:
            return True

    return False
```

#### Cache Performance Metrics

Track these metrics to validate our 60% target:

```python
class CacheMetrics:
    """Track cache performance over time"""

    async def get_cache_performance(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get detailed cache performance metrics"""

        async with get_async_session() as db:
            # Total insights by type
            type_stats = await db.execute(
                select(
                    AIInsight.insight_type,
                    func.count(AIInsight.id).label('total'),
                    func.sum(case((AIInsight.cache_hit == True, 1), else_=0)).label('cache_hits'),
                    func.avg(AIInsight.cost_usd).label('avg_cost'),
                    func.sum(AIInsight.cost_usd).label('total_cost')
                )
                .where(
                    AIInsight.created_at >= start_date,
                    AIInsight.created_at <= end_date
                )
                .group_by(AIInsight.insight_type)
            )

            performance_by_type = {}
            total_insights = 0
            total_cache_hits = 0
            total_cost = 0

            for row in type_stats.fetchall():
                insight_type, total, cache_hits, avg_cost, type_cost = row
                total_insights += total
                total_cache_hits += cache_hits
                total_cost += float(type_cost)

                hit_rate = (cache_hits / total * 100) if total > 0 else 0

                performance_by_type[insight_type] = {
                    'total_generated': total,
                    'cache_hits': cache_hits,
                    'cache_hit_rate': f"{hit_rate:.1f}%",
                    'avg_cost_usd': float(avg_cost),
                    'total_cost_usd': float(type_cost)
                }

            overall_hit_rate = (total_cache_hits / total_insights * 100) if total_insights > 0 else 0

            # Estimate cost without caching
            cost_without_cache = total_cost / (1 - (overall_hit_rate / 100)) if overall_hit_rate < 100 else total_cost * 2
            cost_saved = cost_without_cache - total_cost

            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'overall': {
                    'total_insights': total_insights,
                    'cache_hits': total_cache_hits,
                    'cache_hit_rate': f"{overall_hit_rate:.1f}%",
                    'total_cost_usd': total_cost,
                    'estimated_cost_without_cache': cost_without_cache,
                    'cost_saved_usd': cost_saved,
                    'savings_percentage': f"{(cost_saved / cost_without_cache * 100) if cost_without_cache > 0 else 0:.1f}%"
                },
                'by_insight_type': performance_by_type
            }
```

This caching strategy is what makes the economics work. Without it, costs would be **$2.71/user/month**. With it, we get to **$1.36/user/month** - sustainable at scale and within our 2-7% of revenue target.

---

### Cache Manager Implementation

```python
# app/services/ai_analysis/cache_manager.py

class AnalysisCacheManager:
    """
    Intelligent caching system to minimize LLM costs.

    Features:
    - Similarity-based cache lookup (not just exact match)
    - TTL-based expiration
    - Cache warming for common patterns
    - Personalization of cached results
    """

    async def get_cached_insight(
        self,
        cache_key: str,
        insight_type: str,
        max_age_hours: int
    ) -> Optional[AIInsight]:
        """
        Look for cached insight that matches cache_key.

        Returns cached insight if:
        1. Cache key matches
        2. Created within max_age_hours
        3. Has not expired
        """

        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        async with get_async_session() as db:
            result = await db.execute(
                select(AIInsight)
                .where(
                    AIInsight.cache_key == cache_key,
                    AIInsight.insight_type == insight_type,
                    AIInsight.created_at >= cutoff_time,
                    or_(
                        AIInsight.expires_at.is_(None),
                        AIInsight.expires_at > datetime.utcnow()
                    )
                )
                .order_by(AIInsight.created_at.desc())
                .limit(1)
            )
            cached = result.scalar_one_or_none()

        if cached:
            logger.info(f"Cache HIT for {insight_type}: {cache_key}")
            return cached

        logger.info(f"Cache MISS for {insight_type}: {cache_key}")
        return None

    async def warm_cache(self, portfolio_ids: List[UUID]):
        """
        Pre-generate common insights for specified portfolios.
        Called during off-peak hours to populate cache.
        """

        common_insights = ["daily_summary", "volatility_analysis"]

        tasks = []
        for portfolio_id in portfolio_ids:
            for insight_type in common_insights:
                tasks.append(
                    ai_analysis_service.generate_insight(
                        portfolio_id=portfolio_id,
                        insight_type=insight_type,
                        depth="quick"
                    )
                )

        # Generate in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = len([r for r in results if not isinstance(r, Exception)])
        logger.info(f"Cache warming completed: {successful}/{len(tasks)} successful")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance metrics"""

        async with get_async_session() as db:
            # Total insights generated
            total_result = await db.execute(
                select(func.count(AIInsight.id))
            )
            total_insights = total_result.scalar()

            # Cached variants
            cached_result = await db.execute(
                select(func.count(AIInsight.id))
                .where(AIInsight.is_cached_variant == True)
            )
            cached_insights = cached_result.scalar()

            # Total cost
            cost_result = await db.execute(
                select(func.sum(AIInsight.cost_usd))
            )
            total_cost = cost_result.scalar() or 0

            # Cost saved from caching
            cost_saved_result = await db.execute(
                select(func.sum(AIInsight.cost_usd))
                .where(AIInsight.is_cached_variant == True)
            )
            cost_saved = cost_saved_result.scalar() or 0

        cache_hit_rate = (cached_insights / total_insights * 100) if total_insights > 0 else 0

        return {
            "total_insights": total_insights,
            "cached_insights": cached_insights,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "total_cost_usd": float(total_cost),
            "cost_saved_usd": float(cost_saved),
            "effective_cost_usd": float(total_cost - cost_saved)
        }
```

### Cost Tracker Implementation

```python
# app/services/ai_analysis/cost_tracker.py

class CostTracker:
    """
    Track and control LLM spending.

    Features:
    - Per-user monthly budgets
    - Tiered limits (free/pro/enterprise)
    - Real-time cost monitoring
    - Budget alerts
    """

    async def check_budget(self, portfolio_id: UUID) -> bool:
        """
        Check if portfolio owner has budget remaining.
        Returns False if monthly limit exceeded.
        """

        # Get portfolio owner
        async with get_async_session() as db:
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = portfolio_result.scalar_one()
            user_id = portfolio.user_id

            # Get user tier
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one()
            user_tier = getattr(user, 'subscription_tier', 'free')

        # Get monthly usage
        monthly_cost = await self.get_monthly_cost(user_id)

        # Tiered limits
        limits = {
            "free": 0.50,      # $0.50/month (~10-15 deep analyses)
            "pro": 5.00,       # $5.00/month (~100+ analyses)
            "enterprise": None # Unlimited
        }

        limit = limits.get(user_tier)

        if limit is None:
            return True  # Enterprise has no limit

        if monthly_cost >= limit:
            logger.warning(f"User {user_id} ({user_tier}) exceeded budget: ${monthly_cost:.2f} >= ${limit}")
            return False

        return True

    async def get_monthly_cost(self, user_id: UUID) -> float:
        """Get total LLM cost for user this month"""

        # Start of current month
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)

        async with get_async_session() as db:
            # Get all portfolios for user
            portfolio_result = await db.execute(
                select(Portfolio.id).where(Portfolio.user_id == user_id)
            )
            portfolio_ids = [row[0] for row in portfolio_result.fetchall()]

            if not portfolio_ids:
                return 0.0

            # Sum costs for all portfolios this month
            cost_result = await db.execute(
                select(func.sum(AIInsight.cost_usd))
                .where(
                    AIInsight.portfolio_id.in_(portfolio_ids),
                    AIInsight.created_at >= month_start
                )
            )
            total_cost = cost_result.scalar() or 0.0

        return float(total_cost)

    async def record_usage(
        self,
        portfolio_id: UUID,
        cost_usd: float,
        insight_type: str
    ):
        """
        Record usage for analytics.
        (Cost is already stored in AIInsight, this is for aggregated tracking)
        """

        # Could store in separate usage_logs table for detailed analytics
        logger.info(f"Portfolio {portfolio_id}: {insight_type} cost ${cost_usd:.4f}")

    async def get_cost_breakdown(
        self,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed cost breakdown for user"""

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        async with get_async_session() as db:
            # Get portfolios
            portfolio_result = await db.execute(
                select(Portfolio.id, Portfolio.name).where(Portfolio.user_id == user_id)
            )
            portfolios = {row[0]: row[1] for row in portfolio_result.fetchall()}

            if not portfolios:
                return {"total_cost": 0, "breakdown": []}

            # Get insights with costs
            insights_result = await db.execute(
                select(
                    AIInsight.portfolio_id,
                    AIInsight.insight_type,
                    AIInsight.model_used,
                    func.count(AIInsight.id).label('count'),
                    func.sum(AIInsight.cost_usd).label('total_cost'),
                    func.avg(AIInsight.generation_time_ms).label('avg_time_ms')
                )
                .where(
                    AIInsight.portfolio_id.in_(list(portfolios.keys())),
                    AIInsight.created_at >= cutoff_date
                )
                .group_by(
                    AIInsight.portfolio_id,
                    AIInsight.insight_type,
                    AIInsight.model_used
                )
            )

            breakdown = []
            total_cost = 0

            for row in insights_result.fetchall():
                portfolio_id, insight_type, model, count, cost, avg_time = row
                total_cost += float(cost)

                breakdown.append({
                    "portfolio_name": portfolios[portfolio_id],
                    "insight_type": insight_type,
                    "model": model,
                    "count": count,
                    "cost_usd": float(cost),
                    "avg_generation_time_ms": int(avg_time)
                })

        return {
            "period_days": days,
            "total_cost": total_cost,
            "breakdown": sorted(breakdown, key=lambda x: x['cost_usd'], reverse=True)
        }
```

---

## 6. Example User Experiences

### Automated Daily Insight (Dashboard/Email)

```markdown
📊 Daily Portfolio Insight - Hedge Fund Portfolio
October 18, 2025

⚠️ Volatility Alert: Higher Than Expected

Your portfolio's 21-day realized volatility (18.61%) is significantly higher
than typical for long/short equity strategies (8-12%).

**Key Drivers:**
• Under-hedged: Only 49% hedge ratio (should be 90%+ for market-neutral)
• Tech concentration: 70% of long book in high-vol mega-caps (META 17.6%, MSFT 12.6%)
• Asymmetric hedging: Shorting NFLX doesn't offset META/MSFT risk

**Impact:** Your portfolio behaves like a leveraged long tech bet, not a hedged fund.

**Recommendations:**
1. Increase short exposure from $2M to $3.6M (90% hedge ratio)
2. Add tech shorts: Consider shorting ORCL or SAP to offset MSFT/GOOGL exposure
3. Reduce META position from 17.6% to under 10%

[View Full Analysis →] [Adjust Portfolio →]
```

### On-Demand Deep Dive

User clicks **"Analyze Volatility"** button in Risk Metrics page:

```markdown
# Volatility Analysis: Hedge Fund Portfolio

## Summary
Your portfolio's volatility (18.61%) is 120% higher than expected for a long/short equity
strategy due to under-hedging and concentrated tech exposure.

## Key Findings

1. **Insufficient Hedging (49.2% ratio)**
   - Long exposure: $4,079,420 (13 positions)
   - Short exposure: $2,007,406 (9 positions)
   - Net long: $2,072,015 (51% unhedged)
   - Market-neutral funds typically maintain 90-100% hedge ratios

2. **High-Volatility Long Concentration**
   - META: 17.6% ($717K) - Individual vol ~35% annually
   - MSFT: 12.6% ($514K) - Individual vol ~28% annually
   - GOOGL: 11.2% ($456K) - Individual vol ~30% annually
   - Top 3 tech longs = 41% of portfolio

3. **Sector Mismatch in Hedges**
   - Long: 70% in Tech (social media, cloud, semiconductors)
   - Short: 36% in Tech (streaming), 28% in Industrials/Energy
   - Correlation benefit minimal - different risk factors

4. **Concentrated Short Position**
   - NFLX represents 35.8% of short book
   - Single position risk on short side
   - NFLX vol (40%+) adds to portfolio volatility vs reducing it

## Detailed Analysis

### Volatility Attribution by Position

| Position | Type | Weight | Est. Vol Contribution |
|----------|------|--------|-----------------------|
| META | Long | 17.6% | +4.2% |
| NFLX | Short | -35.8% of shorts | +2.8% |
| MSFT | Long | 12.6% | +2.4% |
| TSLA | Long | 8.6% | +2.1% |
| AMD | Long | 6.9% | +1.8% |

These 5 positions contribute an estimated 13.3% of your 18.61% realized volatility.

### Comparison to Strategy Benchmarks

| Strategy Type | Typical Volatility Range |
|---------------|--------------------------|
| Market Neutral L/S | 6-10% |
| Directional L/S | 10-15% |
| Aggressive Growth | 15-20% |
| **Your Portfolio** | **18.61%** |

Your portfolio is tracking more like an aggressive growth fund than a hedged strategy.

### Hedging Gap Analysis

To achieve 10% volatility (typical for market-neutral):
- **Need to add**: $1,600,000 in tech shorts
- **Suggested positions**: ORCL ($800K), SAP ($400K), CRM ($400K)
- **Expected result**: Volatility drops to ~11.2%

OR

- **Reduce long tech**: Trim META to 10%, MSFT to 8%, GOOGL to 8%
- **Redeploy**: Into defensive sectors (Healthcare, Staples)
- **Expected result**: Volatility drops to ~12.5%

## Recommendations

### Immediate Actions (Next 1-2 Trading Days)

1. **Add Sector-Matched Shorts ($1.6M)**
   ```
   Long Position → Short Hedge
   META → SNAP or PINS (social media)
   MSFT/GOOGL → ORCL or CRM (enterprise tech)
   NVDA/AMD → INTC (semiconductors)
   ```
   **Impact**: Reduces volatility by ~35%, hedge ratio to 85%

2. **Reduce Largest Long Concentration**
   - Trim META from $717K (17.6%) to $430K (10%)
   - Redeploy $287K into defensive positions
   - **Impact**: Reduces single-position risk, volatility by ~8%

### Medium-Term Strategy (Next 30 Days)

3. **Rebalance Short Book**
   - Reduce NFLX from 35.8% of shorts to 15%
   - Distribute across 5-6 positions for diversification
   - **Impact**: More stable hedging, less concentration risk

4. **Implement Volatility Targeting**
   - Set target volatility: 10-12%
   - Monthly rebalancing to maintain target
   - Use market beta (SPY) as hedge ratio reference

### Risk Monitoring

5. **Daily Tracking**
   - Monitor 21-day realized vol vs 10% target
   - Track correlation between long/short books
   - Alert if hedge ratio drops below 80%

---

**Analysis Generated**: Oct 18, 2025, 5:32 PM
**Model**: Claude Sonnet 4
**Data Source**: Portfolio snapshot as of Oct 18, 2025
**Cost**: $0.18 | Generation Time: 2.3s
```

### Chat Q&A Experience

```
User: "Is my Hedge Fund portfolio actually hedged?"

AI: Let me analyze your current hedging... [calls analyze_portfolio_insight tool]

Based on your current positions, your portfolio is significantly under-hedged.

**Current State:**
• Long exposure: $4.08M (13 positions)
• Short exposure: $2.01M (9 positions)
• Hedge ratio: 49.2% ❌

A market-neutral hedge fund typically maintains a 90-100% hedge ratio. Your
portfolio has **$2.07M of unhedged long exposure**, making it directionally long
on the market.

Additionally, your hedges aren't sector-neutral:
• You're long META/MSFT/GOOGL (social media + cloud)
• But shorting NFLX/ROKU/ZM (streaming + video)

These sectors don't move together, so your shorts won't protect you if tech
broadly sells off. For example, if there's a tech selloff, MSFT and GOOGL could
drop 10% while NFLX actually rallies, meaning both sides lose.

**Hedging Quality Score: 3/10**

Would you like me to suggest specific positions to improve your hedging?

---

User: "Yes, what should I do?"

AI: Here's a specific action plan to improve your hedging:

**Phase 1: Add Tech Shorts (Next 1-2 Days)**

Add $1.6M in sector-matched shorts:
1. **Short ORCL $800K** (hedges MSFT + GOOGL cloud exposure)
2. **Short SNAP $400K** (hedges META social media exposure)
3. **Short INTC $400K** (hedges NVDA/AMD semiconductor exposure)

This brings your hedge ratio to 88% and creates sector-neutral pairs.

**Phase 2: Rebalance Existing Shorts (This Week)**

Your NFLX short is too concentrated (36% of short book). Reduce to $600K and add:
- $300K short CRM (more cloud hedge)
- $250K short PINS (more social media hedge)

**Expected Results:**
• Hedge ratio: 90%+ ✅
• Volatility: Drops from 18.6% to ~11.5%
• Market neutrality: High correlation between longs/shorts

**Cost:** ~$1.6M in new short positions
**Risk reduction:** Portfolio volatility cut by 38%

Would you like me to generate a detailed trading plan with specific entry prices?
```

---

## 7. Implementation Phases

### **Phase 1: Foundation** (Weeks 1-2)

**Database & Models**
- [ ] Create `ai_insights` table (migration)
- [ ] Create `ai_insight_templates` table (migration)
- [ ] Add `AIInsight` model to `app/models/ai_insights.py`
- [ ] Add `AIInsightTemplate` model
- [ ] Create relationships with Portfolio model
- [ ] Run migrations

**Service Layer**
- [ ] Create `app/services/ai_analysis/` directory structure
- [ ] Implement `analysis_service.py` (core orchestrator)
- [ ] Implement `prompt_builder.py` (Jinja2 rendering)
- [ ] Implement `context_builder.py` (data gathering)
- [ ] Add Anthropic SDK: `uv add anthropic`
- [ ] Implement `providers/anthropic_provider.py`
- [ ] Implement `providers/openai_provider.py` (leverage existing)

**Prompt Templates**
- [ ] Create 3 initial templates:
  - `volatility_analysis.j2`
  - `concentration_risk.j2`
  - `daily_summary.j2`
- [ ] Create seeder script: `scripts/seed_ai_templates.py`
- [ ] Test template rendering with sample data

**Deliverable**: Working analysis service that can generate insights

---

### **Phase 2: Automated Daily Insights** (Week 3)

**Batch Integration**
- [ ] Create `app/batch/jobs/ai_insights_generator.py`
- [ ] Add `_generate_ai_insights()` to batch orchestrator
- [ ] Run after portfolio snapshot creation
- [ ] Add error handling and retries

**API Endpoints**
- [ ] Create `app/api/v1/insights.py` router
- [ ] Implement `GET /api/v1/insights/daily/{portfolio_id}`
- [ ] Implement `GET /api/v1/insights/latest/{portfolio_id}`
- [ ] Add to main API router
- [ ] Test endpoints

**Frontend Integration**
- [ ] Create `DailyInsight` component in frontend
- [ ] Add to dashboard page
- [ ] Style with severity indicators (info/warning/alert)
- [ ] Add "View Full Analysis" modal

**Testing**
- [ ] Run batch processing manually
- [ ] Verify insights generated for all portfolios
- [ ] Check daily insight quality
- [ ] Validate API responses

**Deliverable**: Users see daily AI-generated insights on dashboard

---

### **Phase 3: On-Demand Deep Analysis** (Week 4)

**Deep Analysis Features**
- [ ] Implement `POST /api/v1/insights/analyze` endpoint
- [ ] Add model selection UI (OpenAI vs Anthropic)
- [ ] Implement `cache_manager.py` with smart caching
- [ ] Add cache statistics tracking

**Cost Controls**
- [ ] Implement `cost_tracker.py`
- [ ] Add budget checking to analysis service
- [ ] Create tiered limits (free/pro/enterprise)
- [ ] Add cost dashboard endpoint

**Frontend**
- [ ] Create "Deep Analysis" button in Risk Metrics page
- [ ] Build analysis results modal/page
- [ ] Add model selector dropdown
- [ ] Show key findings as bullet points
- [ ] Display recommendations prominently
- [ ] Add feedback mechanism (rating 1-5 stars)

**Deliverable**: Users can request detailed on-demand analysis

---

### **Phase 4: Chat Integration** (Week 5)

**Tool Development**
- [ ] Add `analyze_portfolio_insight` tool to chat
- [ ] Add `get_latest_insight` tool to chat
- [ ] Update system prompts to include analysis capabilities
- [ ] Test conversational flow

**Streaming Support**
- [ ] Handle long-running analysis in chat (progress indicators)
- [ ] Add SSE events for analysis generation
- [ ] Show "Analyzing..." state in chat UI

**Enhanced Prompts**
- [ ] Add context-aware question routing
- [ ] Detect when to use cached insights vs fresh analysis
- [ ] Improve follow-up question handling

**Deliverable**: Users can ask analytical questions in chat

---

### **Phase 5: Optimization & Scale** (Weeks 6+)

**Caching Optimization**
- [ ] Implement cache warming (pre-generate common insights)
- [ ] Add similarity-based cache matching
- [ ] Optimize cache hit rate (target >60%)
- [ ] Add cache expiration policies

**Cost Optimization**
- [ ] Implement tiered pricing
- [ ] Add usage alerts (80% of budget warning)
- [ ] Create cost analytics dashboard
- [ ] A/B test cheaper models for simple analyses

**Quality Monitoring**
- [ ] Track user feedback ratings
- [ ] Monitor generation times
- [ ] Detect and alert on low-quality outputs
- [ ] Implement prompt versioning and A/B testing

**Scale Testing**
- [ ] Load test with 1000 concurrent analysis requests
- [ ] Optimize database queries (add indexes)
- [ ] Implement request queuing for rate limits
- [ ] Test cache under load

**Deliverable**: Production-ready system optimized for scale

---

## 8. Success Metrics

### **Engagement Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily insight open rate | >40% | % of users who view daily insights |
| Deep analysis requests/user/month | 2-5 | Avg requests per active user |
| Chat analysis tool usage | >20% | % of chat sessions using analysis tools |
| Feedback ratings | >4.0/5.0 | Avg user rating on insights |

### **Technical Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache hit rate | >60% | % of insights served from cache |
| P95 generation time | <3s | 95th percentile latency |
| Analysis accuracy | >85% | User feedback "helpful" rate |
| Cost per active user | <$2.00 | Monthly LLM cost / active user |

### **Business Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Feature adoption | >50% | % of users using AI analysis |
| User retention lift | +10% | Retention improvement vs control |
| Premium conversion | +5% | Increase in free→pro upgrades |
| Support ticket reduction | -20% | Reduction in "why" questions |

---

## 9. Technical Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **LLM hallucinations** | Medium | High | • Include source data in analysis<br>• Add validation layer<br>• User feedback loop |
| **Cost overruns** | Medium | High | • Hard budget limits per tier<br>• Aggressive caching<br>• Cost monitoring alerts |
| **API rate limits** | Medium | Medium | • Request queuing<br>• Multiple API keys<br>• Fallback models |
| **Latency issues** | Low | Medium | • Use GPT-4o for speed<br>• Pre-generate common analyses<br>• Async processing |
| **Stale insights** | Medium | Low | • TTL-based cache expiry<br>• Regenerate on portfolio changes<br>• Show timestamp |
| **Model degradation** | Low | Medium | • A/B test prompt changes<br>• Track quality metrics<br>• Multi-provider fallback |
| **Privacy concerns** | Low | High | • Never send PII to LLMs<br>• Use anonymized data patterns<br>• SOC 2 compliance |

---

## 10. Future Enhancements

### **Advanced Features** (Post-MVP)

1. **Multi-Portfolio Analysis**
   - Compare volatility across user's portfolios
   - Suggest rebalancing between portfolios
   - Consolidated risk reporting

2. **Predictive Insights**
   - "Your volatility is likely to increase next week" (using HAR forecast)
   - "Position XYZ is diverging from your strategy"
   - Proactive recommendations before issues arise

3. **Natural Language Queries**
   - "Show me all portfolios with volatility above 15%"
   - "Which positions contribute most to my tech exposure?"
   - SQL generation from natural language

4. **Personalized Learning**
   - Learn from user feedback to improve prompts
   - Adapt analysis style to user preferences (technical vs simple)
   - Remember user's risk tolerance and goals

5. **Multi-Modal Analysis**
   - Include charts and visualizations in LLM context
   - Generate annotated charts highlighting insights
   - Voice-based analysis (audio summaries)

6. **Collaborative Analysis**
   - Share insights with advisors/team members
   - Comment threads on insights
   - Team alerts for critical findings

---

## 11. Cost Model Details

### **Pricing Breakdown** (as of Oct 2025)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Best For |
|-------|----------------------|------------------------|----------|
| **GPT-4o** | $2.50 | $10.00 | Standard analysis, chat |
| **GPT-4o-mini** | $0.15 | $0.60 | Daily summaries, quick insights |
| **Claude Sonnet 4** | $3.00 | $15.00 | Deep analysis, complex reasoning |
| **Claude Opus 4** | $15.00 | $75.00 | Premium analysis (rarely needed) |

### **Token Usage Estimates**

**Daily Summary** (GPT-4o-mini)
- Input: 3,000 tokens (portfolio context)
- Output: 300 tokens (brief summary)
- Cost: $0.0007 per summary

**Volatility Analysis** (Claude Sonnet)
- Input: 5,000 tokens (comprehensive context)
- Output: 2,000 tokens (detailed analysis)
- Cost: $0.045 per analysis

**Chat Q&A** (GPT-4o)
- Input: 4,000 tokens (context + history)
- Output: 800 tokens (conversational response)
- Cost: $0.018 per message

### **Monthly Cost Projection per User**

**Active User** (50% of users):
- Daily summaries: 60× × $0.0007 = $0.042
- Volatility deep dives: 2× × $0.045 = $0.090
- Concentration analysis: 2× × $0.040 = $0.080
- Chat interactions: 24× × $0.018 = $0.432
- **Total: ~$0.64/month** (before caching)

**With 60% Cache Hit Rate**:
- Effective cost: $0.64 × 0.40 = **$0.26/month per active user**

**At Scale (100K users, 50% active)**:
- 50,000 active users × $0.26 = **$13,000/month**
- Add 20% for spikes/growth = **$15,600/month**

Much lower than initial $34K estimate thanks to caching!

---

## 12. Development Timeline

### **8-Week Implementation Plan**

```
Week 1-2: Foundation
├── Database schema & migrations
├── Service layer architecture
├── LLM provider integrations
└── Initial prompt templates

Week 3: Automated Insights
├── Batch job integration
├── API endpoints
├── Frontend dashboard component
└── Testing & refinement

Week 4: On-Demand Analysis
├── Deep analysis endpoint
├── Cache management
├── Cost tracking
└── Frontend analysis UI

Week 5: Chat Integration
├── Chat tool development
├── Streaming support
├── Enhanced prompts
└── Testing

Week 6-7: Optimization
├── Cache warming
├── Cost optimization
├── A/B testing framework
└── Quality monitoring

Week 8: Scale Testing
├── Load testing
├── Database optimization
├── Rate limit handling
└── Production readiness
```

**Target Launch**: Week 9 (Beta), Week 10 (GA)

---

## 13. Next Steps

### **Immediate Actions**

1. **Architecture Review Meeting**
   - Review this plan with engineering team
   - Discuss technical approach
   - Identify dependencies
   - Assign ownership

2. **Cost Model Validation**
   - Test actual token usage with sample portfolios
   - Validate pricing assumptions
   - Finalize tier limits

3. **Prompt Engineering Workshop**
   - Write first drafts of all 3 templates
   - Test with demo portfolios
   - Iterate on quality

4. **Database Design Review**
   - Finalize schema
   - Identify indexes needed
   - Plan migration strategy

### **Week 1 Deliverables**

- [ ] Database migrations created and tested
- [ ] Service layer structure established
- [ ] Anthropic integration working
- [ ] First template rendering successfully
- [ ] Basic cost tracking implemented

---

## 9. REFINED IMPLEMENTATION PLAN: Analytical Reasoning Layer

> **Updated based on deep discussion:** This plan reflects the distinction between Q&A chat (existing) vs. investigative analytical reasoning (new capability).

### Core Principles

1. **Free-Form Investigation**: AI scans all metrics, decides what's interesting, investigates root causes
2. **Hybrid Data Access**: Prefer batch results → fall back to APIs → calculate on-demand
3. **Graceful Degradation**: Handle incomplete/unreliable calculation data transparently
4. **Analytical Tools**: Higher-level reasoning tools, not just data-fetching
5. **Both Proactive & On-Demand**: Nightly auto-investigation + user-triggered deep analysis

---

### Phase 1: Core Analytical Reasoning Engine (Weeks 1-2)

**Build the investigative AI system that reasons, not just retrieves.**

**Components:**

1. **`AnalyticalReasoningService`** (`app/services/ai_analysis/reasoning_service.py`)
   - Core investigation orchestration
   - Free-form vs. focused investigation modes
   - Tool calling with analytical tools (not data tools)
   - Structured insight generation

2. **Hybrid Context Builder** (`app/services/ai_analysis/context_builder.py`)
   - Gather batch calculation results (volatility, stress, beta, correlation)
   - Fall back to API calls for missing data
   - Calculate analytical metrics on-demand (hedge quality, concentration, etc.)
   - Assess data quality for each metric (complete/partial/incomplete/unreliable)

3. **Analytical Tools Registry** (`app/services/ai_analysis/analytical_tools.py`)
   - `calculate_hedge_quality_metrics()` - hedge ratio, sector alignment, correlation benefit
   - `analyze_volatility_attribution()` - position-level vol contribution
   - `compare_to_strategy_benchmarks()` - expected ranges, deviations, severity
   - `identify_concentration_risks()` - HHI, sector concentration, top-N risk
   - `diagnose_calculation_anomalies()` - help debug unreliable calculations

4. **Anthropic Claude Sonnet 4 Provider** (`app/services/ai_analysis/providers/anthropic_provider.py`)
   - Integration with Claude Sonnet 4 API
   - Stream handling for long investigations
   - Tool calling support
   - Cost tracking

5. **Free-Form Investigation Prompts** (`app/agent/prompts/investigation_prompts.py`)
   ```python
   FREE_FORM_PROMPT = """
   You are a senior portfolio analyst conducting comprehensive review.

   INVESTIGATION APPROACH:
   1. SCAN all metrics - identify anything noteworthy
   2. FORM HYPOTHESES about root causes
   3. TEST HYPOTHESES using analytical tools
   4. COMPARE to strategy benchmarks
   5. CONNECT disparate metrics
   6. SYNTHESIZE into actionable insights

   DATA QUALITY: Some calculations incomplete/unreliable (marked).
   Focus on reliable data, be transparent about limitations.

   Think like analyst doing due diligence, not chatbot answering questions.
   """
   ```

**Deliverables:**
- ✅ Core investigation service
- ✅ Hybrid data access with quality assessment
- ✅ 5 analytical tools
- ✅ Anthropic provider
- ✅ Investigation prompt templates

---

### Phase 2: Automated Nightly Investigation (Week 3)

**Add Phase 9 to batch orchestrator for proactive insights.**

**Integration:**

```python
# app/batch/batch_orchestrator_v2.py - Add Phase 9

async def run_daily_batch_sequence(portfolio_id: Optional[UUID] = None):
    # ... Phases 1-8 (existing calculations) ...

    # Phase 9: AI Analytical Investigation (NEW)
    try:
        for portfolio in portfolios:
            insight = await analytical_reasoning_service.investigate_portfolio(
                portfolio_id=portfolio.id,
                focus_area=None  # Free-form - AI decides what's interesting
            )

            await store_insight(insight)

            if insight.severity in ["warning", "critical"]:
                await queue_user_notification(portfolio.user_id, insight)

    except Exception as e:
        logger.error(f"Phase 9 failed: {e}")
        # Graceful degradation - don't block other phases
```

**Deliverables:**
- ✅ Batch integration (Phase 9)
- ✅ Automated nightly investigation
- ✅ Insight storage
- ✅ Notification system (dashboard flag + email queue)
- ✅ Dashboard UI to display latest insights

---

### Phase 3: On-Demand Deep Analysis (Week 4)

**Add UI-triggered investigative analysis.**

**Components:**

1. **"Deep Analysis" Buttons** on Risk Metrics page
2. **Analysis Panel Component** to display structured insights
3. **On-Demand API Endpoint** (`POST /api/v1/insights/analyze`)
4. **"Ask Follow-Up Questions" Integration** with existing chat

**User Flow:**
- User clicks "Deep Analysis" on volatility metric
- Triggers focused investigation on volatility
- Analysis Panel streams results
- User can click "Ask Follow-Up Questions" → opens chat with context

**Deliverables:**
- ✅ Deep Analysis buttons on metrics
- ✅ Analysis Panel component
- ✅ On-demand API endpoint
- ✅ Chat integration for follow-ups
- ✅ Loading/streaming states

---

### Phase 4: Enhanced Analytical Tools (Week 5)

**Expand toolkit for comprehensive investigations.**

**Additional Tools:**

- `analyze_factor_tilts()` - factor exposure analysis
- `assess_drawdown_risk()` - max drawdown estimation
- `identify_portfolio_drift()` - strategy/sector/risk drift over time
- `recommend_rebalancing_actions()` - specific trade recommendations

**Deliverables:**
- ✅ 4 additional analytical tools
- ✅ Tool testing with demo portfolios
- ✅ Prompt refinement based on tool usage
- ✅ Methodology documentation

---

### Phase 5: Optimization & Quality (Weeks 6-7)

**Add caching, cost controls, quality monitoring.**

**Components:**

1. **Smart Caching** (mostly for on-demand)
   - Cache on-demand analyses for 24 hours
   - Nightly insights don't need caching (run once)

2. **Cost Tracking & Budget Controls**
   - Track per-user analytical costs separately from chat
   - Monthly budget limits per tier
   - Usage analytics dashboard

3. **Quality Monitoring**
   - Assess insight quality (grounded in data, actionable, acknowledges limitations)
   - Collect user feedback (1-5 stars + comments)
   - Iterate prompts based on feedback

**Deliverables:**
- ✅ Smart caching system
- ✅ Cost tracking and budgets
- ✅ Quality monitoring
- ✅ User feedback UI
- ✅ Analytics dashboard

---

### Phase 6: Production Hardening (Week 8)

**Make system production-ready.**

**Tasks:**
- Error handling for all edge cases
- Graceful degradation when calculations unavailable
- Performance optimization
- Security review (prompt injection prevention)
- Load testing
- Documentation
- User onboarding

---

### Cost Reality Check

**Current Scale (3 portfolios):**
- Nightly: 3 × 30 days = 90 analyses/month @ $0.045 = **$4.05/month**
- On-demand: ~24 analyses/month @ $0.045 = **$1.08/month**
- **Total: ~$5/month** (negligible)

**Caching ROI at this scale**: Saves ~$2-3/month. Build it for future, don't over-optimize now.

**When to optimize**: At 100+ portfolios with >1000 on-demand requests/month.

---

## Appendix A: Sample Prompts

### Volatility Analysis (Full Template)

See Section 3 for complete Jinja2 template.

### Daily Summary Examples

**Input Data:**
```json
{
  "portfolio": {
    "name": "Hedge Fund Portfolio",
    "total_value": 6670826.50,
    "daily_change": -42315.80
  },
  "top_mover": {
    "symbol": "META",
    "direction": "down",
    "change_pct": -0.0342
  },
  "volatility": {
    "realized_21d": 0.1861
  }
}
```

**Generated Output:**
```
Your Hedge Fund Portfolio declined $42.3K (-0.6%) today, driven primarily by
META's 3.4% drop. Portfolio volatility remains elevated at 18.6%, well above
the 8-12% range typical for long/short strategies. Consider reviewing hedge
positions to reduce market sensitivity.
```

---

## Appendix B: API Examples

### Generate On-Demand Analysis

```bash
curl -X POST "https://api.sigmasight.io/api/v1/insights/analyze" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": "fcd71196-e93e-f000-5a74-31a9eead3118",
    "insight_type": "volatility_analysis",
    "model": "claude-sonnet-4",
    "depth": "deep",
    "user_question": "Why is my volatility so high compared to other hedge funds?"
  }'
```

**Response:**
```json
{
  "id": "a7b3c9d1-...",
  "portfolio_id": "fcd71196-...",
  "insight_type": "volatility_analysis",
  "title": "Volatility Alert: Under-Hedged Tech Concentration",
  "summary": "Your portfolio's 18.61% volatility is 120% higher than expected...",
  "full_analysis": "# Volatility Analysis: Hedge Fund Portfolio\n\n## Summary...",
  "key_findings": [
    "Insufficient hedging (49.2% ratio vs 90%+ target)",
    "High-volatility long concentration in tech (70% of longs)",
    "Sector mismatch in hedges (tech longs, industrial shorts)"
  ],
  "recommendations": [
    "Add $1.6M in sector-matched tech shorts",
    "Reduce META position from 17.6% to under 10%",
    "Rebalance short book to reduce NFLX concentration"
  ],
  "severity": "warning",
  "model_used": "claude-sonnet-4",
  "cost_usd": 0.18,
  "generation_time_ms": 2300
}
```

---

## Appendix C: Caching Strategy

### Cache Key Generation Logic

```python
# Example cache key for volatility analysis

portfolio_characteristics = {
    "insight_type": "volatility_analysis",
    "strategy_type": "long_short_equity",
    "num_positions_bucket": "medium",  # 10-30 positions
    "volatility_bucket": "high",        # >20% vol
    "total_value_bucket": "hnw"         # $1M-$10M
}

cache_key = "volatility_analysis:a3f8c9e2"
```

### Cache Matching Examples

**Scenario 1: Exact Match**
```
Portfolio A: Long/Short, 22 positions, 18.5% vol, $5.2M
Portfolio B: Long/Short, 24 positions, 19.2% vol, $4.8M
→ CACHE HIT (same bucket characteristics)
→ Reuse analysis with minor personalization
```

**Scenario 2: Different Bucket**
```
Portfolio A: Long/Short, 22 positions, 18.5% vol, $5.2M
Portfolio C: Long/Short, 45 positions, 18.8% vol, $5.1M
→ CACHE MISS (different position count bucket)
→ Generate fresh analysis
```

### Personalization Layer

Even with cache hit, personalize:
- Portfolio name
- Exact values (use buckets for matching, exact for display)
- Top positions list
- Specific recommendations

---

**End of Document**

*This architecture is designed for production deployment at scale while maintaining cost efficiency and high quality. All components are modular and can be implemented incrementally.*
