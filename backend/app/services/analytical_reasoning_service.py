"""
Analytical Reasoning Service - AI-powered portfolio investigation and analysis.

This service provides multi-step analytical reasoning for portfolio risk metrics,
going beyond simple data retrieval to investigate root causes and synthesize insights.

Key Capabilities:
- Proactive anomaly detection across all portfolio metrics
- Multi-step hypothesis formation and testing
- Synthesis of disparate data points into actionable insights
- Transparent handling of incomplete/unreliable calculation data
- Smart caching to reduce costs
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.ai_insights import AIInsight, InsightType, InsightSeverity
from app.models.users import Portfolio
from app.services.anthropic_provider import anthropic_provider
from app.services.hybrid_context_builder import hybrid_context_builder

logger = get_logger(__name__)


class AnalyticalReasoningService:
    """
    Orchestrates AI-powered analytical reasoning for portfolio analysis.

    This service is the main entry point for generating portfolio insights using
    multi-step AI investigation.
    """

    def __init__(self):
        """Initialize the analytical reasoning service."""
        self.model_name = "claude-sonnet-4"
        self.provider = "anthropic"
        logger.info("AnalyticalReasoningService initialized")

    async def investigate_portfolio(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        insight_type: InsightType = InsightType.DAILY_SUMMARY,
        focus_area: Optional[str] = None,
        user_question: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> AIInsight:
        """
        Conduct AI-powered investigation of portfolio metrics.

        This is the main entry point for portfolio analysis. It:
        1. Checks cache for similar recent analyses
        2. Builds hybrid investigation context
        3. Executes free-form AI investigation
        4. Stores and returns the insight

        Args:
            db: Database session
            portfolio_id: UUID of portfolio to investigate
            insight_type: Type of insight to generate
            focus_area: Optional focus area (e.g., "volatility", "concentration")
            user_question: Optional user question for on-demand analysis
            auth_token: Optional JWT token for authenticating tool API calls

        Returns:
            AIInsight: Generated insight with analysis and recommendations

        Raises:
            ValueError: If portfolio not found
        """
        logger.info(
            f"Starting investigation: portfolio={portfolio_id}, type={insight_type.value}, "
            f"focus={focus_area}, question={user_question[:50] if user_question else None}"
        )

        # 1. Verify portfolio exists
        portfolio = await self._get_portfolio(db, portfolio_id)

        # 2. Check cache for similar analysis (DISABLED FOR DEVELOPMENT)
        cache_key = self._generate_cache_key(portfolio_id, insight_type, focus_area, user_question)
        # cached_insight = await self._check_cache(db, cache_key)
        # if cached_insight:
        #     logger.info(f"Cache hit for investigation: {cache_key[:16]}...")
        #     return cached_insight

        # 3. Build investigation context
        context = await self._build_investigation_context(db, portfolio_id, focus_area)

        # 4. Execute AI investigation (placeholder - will implement with Claude integration)
        insight_data = await self._execute_investigation(
            portfolio_id=portfolio_id,
            insight_type=insight_type,
            context=context,
            focus_area=focus_area,
            user_question=user_question,
            auth_token=auth_token,
        )

        # 5. Store insight in database
        insight = await self._store_insight(
            db=db,
            portfolio_id=portfolio_id,
            insight_type=insight_type,
            insight_data=insight_data,
            context=context,
            cache_key=cache_key,
            focus_area=focus_area,
            user_question=user_question,
        )

        logger.info(f"Investigation complete: {insight.id}")
        return insight

    async def _get_portfolio(self, db: AsyncSession, portfolio_id: UUID) -> Portfolio:
        """Get portfolio from database."""
        result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            raise ValueError(f"Portfolio not found: {portfolio_id}")

        return portfolio

    def _generate_cache_key(
        self,
        portfolio_id: UUID,
        insight_type: InsightType,
        focus_area: Optional[str],
        user_question: Optional[str],
    ) -> str:
        """
        Generate cache key for insight lookup.

        Cache key includes portfolio characteristics and query parameters
        to enable similarity matching.
        """
        cache_input = {
            "portfolio_id": str(portfolio_id),
            "insight_type": insight_type.value,
            "focus_area": focus_area,
            "question_hash": hashlib.md5(user_question.encode()).hexdigest() if user_question else None,
        }

        cache_string = json.dumps(cache_input, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()

    async def _check_cache(self, db: AsyncSession, cache_key: str) -> Optional[AIInsight]:
        """
        Check if similar analysis exists in cache (last 24 hours).

        Returns cached insight if:
        - Cache key matches
        - Created within last 24 hours
        - Not expired
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        result = await db.execute(
            select(AIInsight)
            .where(
                AIInsight.cache_key == cache_key,
                AIInsight.created_at >= cutoff_time,
                (AIInsight.expires_at.is_(None) | (AIInsight.expires_at > datetime.utcnow())),
            )
            .order_by(AIInsight.created_at.desc())
            .limit(1)
        )

        cached_insight = result.scalar_one_or_none()

        if cached_insight:
            # Update cache hit metadata
            cached_insight.cache_hit = True
            await db.commit()

        return cached_insight

    async def _build_investigation_context(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        focus_area: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build hybrid investigation context from batch results and API data.

        This is a placeholder implementation. Will be enhanced with:
        - Batch calculation results (volatility, Greeks, correlations, etc.)
        - Real-time market data
        - Data quality assessments
        - Historical trends

        Returns:
            Dict containing portfolio metrics and data quality flags
        """
        logger.info(f"Building investigation context for portfolio {portfolio_id}")

        # Use hybrid context builder to aggregate real portfolio data
        context = await hybrid_context_builder.build_context(
            db=db,
            portfolio_id=portfolio_id,
            focus_area=focus_area,
        )

        return context

    async def _execute_investigation(
        self,
        portfolio_id: UUID,
        insight_type: InsightType,
        context: Dict[str, Any],
        focus_area: Optional[str],
        user_question: Optional[str],
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute AI-powered investigation using Claude Sonnet 4.

        Delegates to AnthropicProvider for actual investigation.

        Args:
            portfolio_id: Portfolio UUID
            insight_type: Type of insight to generate
            context: Investigation context with portfolio data
            focus_area: Optional focus area
            user_question: Optional user question
            auth_token: Optional JWT token for tool authentication

        Returns:
            Dict containing analysis results
        """
        logger.info(f"Executing AI investigation: type={insight_type.value}")

        # Call Anthropic provider for investigation with auth token for tool calls
        result = await anthropic_provider.investigate(
            context=context,
            insight_type=insight_type,
            focus_area=focus_area,
            user_question=user_question,
            auth_token=auth_token,
        )

        return result

    async def _store_insight(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        insight_type: InsightType,
        insight_data: Dict[str, Any],
        context: Dict[str, Any],
        cache_key: str,
        focus_area: Optional[str],
        user_question: Optional[str],
    ) -> AIInsight:
        """
        Store generated insight in database.

        Args:
            db: Database session
            portfolio_id: Portfolio UUID
            insight_type: Type of insight
            insight_data: Analysis results from AI
            context: Investigation context
            cache_key: Cache key for lookup
            focus_area: Optional focus area
            user_question: Optional user question

        Returns:
            Stored AIInsight object
        """
        insight = AIInsight(
            id=uuid4(),
            portfolio_id=portfolio_id,
            insight_type=insight_type.value if isinstance(insight_type, InsightType) else insight_type,
            title=insight_data["title"],
            severity=insight_data["severity"].value if isinstance(insight_data["severity"], InsightSeverity) else insight_data["severity"],
            summary=insight_data["summary"],
            full_analysis=insight_data.get("full_analysis"),
            key_findings=insight_data.get("key_findings"),
            recommendations=insight_data.get("recommendations"),
            data_limitations=insight_data.get("data_limitations"),
            context_data=context,
            data_quality=context.get("data_quality"),
            focus_area=focus_area,
            user_question=user_question,
            model_used=self.model_name,
            provider=self.provider,
            prompt_version="1.0.0",  # Will come from template
            cost_usd=insight_data["performance"].get("cost_usd"),
            generation_time_ms=insight_data["performance"].get("generation_time_ms"),
            token_count_input=insight_data["performance"].get("token_count_input"),
            token_count_output=insight_data["performance"].get("token_count_output"),
            tool_calls_count=insight_data["performance"].get("tool_calls_count", 0),
            cache_hit=False,
            cache_key=cache_key,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(insight)
        await db.commit()
        await db.refresh(insight)

        logger.info(f"Stored insight: {insight.id}")
        return insight


# Singleton instance
analytical_reasoning_service = AnalyticalReasoningService()
