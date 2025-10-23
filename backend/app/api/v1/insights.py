"""
AI Insights API Endpoints

Endpoints for generating and managing AI-powered portfolio insights using Claude Sonnet 4.
Insights analyze portfolio data (positions, risk metrics, volatility, spread factors, etc.)
and provide actionable recommendations.

**Key Features**:
- Generate insights on-demand (~$0.02, 25-30 seconds)
- 7 insight types (Daily Summary, Volatility Analysis, Concentration Risk, etc.)
- Smart 24-hour caching to reduce costs
- User feedback/rating system
- Cost and performance tracking

**Endpoints**:
- POST   /insights/generate                → Generate new insight
- GET    /insights/portfolio/{portfolio_id} → List portfolio insights
- GET    /insights/{insight_id}            → Get single insight
- PATCH  /insights/{insight_id}            → Update insight metadata
- POST   /insights/{insight_id}/feedback   → Submit feedback/rating

**Backend Integration**:
- Service: app/services/analytical_reasoning_service.py (investigate_portfolio)
- Context Builder: app/services/hybrid_context_builder.py (aggregates portfolio data)
- AI Provider: app/services/anthropic_provider.py (Claude Sonnet 4)
- Models: app/models/ai_insights.py (AIInsight, AIInsightTemplate)

Created: 2025-10-22
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from pydantic import BaseModel, Field

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.schemas.auth import CurrentUser
from app.models.ai_insights import AIInsight, InsightType, InsightSeverity
from app.services.analytical_reasoning_service import analytical_reasoning_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class GenerateInsightRequest(BaseModel):
    """Request to generate a new AI insight"""
    portfolio_id: str = Field(..., description="Portfolio UUID")
    insight_type: str = Field(..., description="Type of insight to generate")
    focus_area: Optional[str] = Field(None, description="Optional focus area (e.g., 'tech exposure', 'options risk')")
    user_question: Optional[str] = Field(None, description="Optional custom question for 'custom' insight type")


class InsightPerformance(BaseModel):
    """Performance metrics for insight generation"""
    cost_usd: float = Field(..., description="Cost in USD")
    generation_time_ms: int = Field(..., description="Time taken in milliseconds")
    token_count: int = Field(..., description="Total tokens used")


class AIInsightResponse(BaseModel):
    """Single AI insight response"""
    id: str
    portfolio_id: str
    insight_type: str
    title: str
    severity: str
    summary: str
    key_findings: List[str]
    recommendations: List[str]
    full_analysis: str
    data_limitations: str
    focus_area: Optional[str] = None
    user_question: Optional[str] = None
    created_at: str
    viewed: bool
    dismissed: bool
    user_rating: Optional[float] = None
    user_feedback: Optional[str] = None
    performance: InsightPerformance

    class Config:
        from_attributes = True


class InsightsListResponse(BaseModel):
    """List of insights with pagination"""
    insights: List[AIInsightResponse]
    total: int
    has_more: bool


class UpdateInsightRequest(BaseModel):
    """Request to update insight metadata"""
    viewed: Optional[bool] = None
    dismissed: Optional[bool] = None


class InsightFeedbackRequest(BaseModel):
    """Request to submit feedback on an insight"""
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1-5")
    feedback: Optional[str] = Field(None, description="Optional text feedback")


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/generate", response_model=AIInsightResponse, status_code=status.HTTP_201_CREATED)
async def generate_insight(
    request: GenerateInsightRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new AI insight for a portfolio.

    **Process**:
    1. Validates portfolio ownership
    2. Checks for cached insights (24-hour window)
    3. Aggregates portfolio data (positions, risk, volatility, spread factors, etc.)
    4. Sends to Claude Sonnet 4 for analysis
    5. Saves insight to database
    6. Returns structured insight

    **Cost**: ~$0.02 per generation
    **Time**: 25-30 seconds

    **Rate Limiting**: Max 10 insights per portfolio per day

    **Insight Types**:
    - daily_summary: Comprehensive portfolio review
    - volatility_analysis: Volatility patterns and risk factors
    - concentration_risk: Concentration and diversification analysis
    - hedge_quality: Hedge effectiveness evaluation
    - factor_exposure: Factor exposure and systematic risk
    - stress_test_review: Stress test results analysis
    - custom: Custom user question

    **Returns**:
        AIInsightResponse with analysis, findings, recommendations, and performance metrics
    """
    try:
        # Validate portfolio ownership
        portfolio_id = UUID(request.portfolio_id)
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Check rate limiting (max 10 per portfolio per day)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count_stmt = select(func.count(AIInsight.id)).where(
            and_(
                AIInsight.portfolio_id == portfolio_id,
                AIInsight.created_at >= today_start
            )
        )
        count_result = await db.execute(count_stmt)
        count = count_result.scalar()

        if count >= 10:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily insight generation limit reached (10 per portfolio per day)"
            )

        # Convert insight_type string to enum
        try:
            insight_type_enum = InsightType(request.insight_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid insight_type. Must be one of: {', '.join([t.value for t in InsightType])}"
            )

        # Generate insight using analytical reasoning service
        logger.info(f"Generating {request.insight_type} insight for portfolio {portfolio_id}")

        insight = await analytical_reasoning_service.investigate_portfolio(
            db=db,
            portfolio_id=portfolio_id,
            insight_type=insight_type_enum,
            focus_area=request.focus_area,
            user_question=request.user_question
        )

        if not insight:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate insight"
            )

        logger.info(f"Generated insight {insight.id} (cost: ${insight.cost_usd:.4f}, time: {insight.generation_time_ms}ms)")

        # Build response
        return AIInsightResponse(
            id=str(insight.id),
            portfolio_id=str(insight.portfolio_id),
            insight_type=insight.insight_type.value,
            title=insight.title,
            severity=insight.severity.value,
            summary=insight.summary,
            key_findings=insight.key_findings or [],
            recommendations=insight.recommendations or [],
            full_analysis=insight.full_analysis or "",
            data_limitations=insight.data_limitations or "",
            focus_area=insight.focus_area,
            user_question=insight.user_question,
            created_at=insight.created_at.isoformat(),
            viewed=insight.viewed,
            dismissed=insight.dismissed,
            user_rating=float(insight.user_rating) if insight.user_rating else None,
            user_feedback=insight.user_feedback,
            performance=InsightPerformance(
                cost_usd=float(insight.cost_usd) if insight.cost_usd else 0.0,
                generation_time_ms=insight.generation_time_ms or 0,
                token_count=insight.token_count or 0
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating insight: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error generating insight"
        )


@router.get("/portfolio/{portfolio_id}", response_model=InsightsListResponse)
async def list_portfolio_insights(
    portfolio_id: UUID,
    insight_type: Optional[str] = Query(None, description="Filter by insight type"),
    days_back: int = Query(30, ge=1, le=365, description="How many days back to fetch"),
    limit: int = Query(20, ge=1, le=100, description="Max number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List insights for a portfolio with optional filtering and pagination.

    **Query Parameters**:
    - insight_type: Filter by specific insight type (optional)
    - days_back: How far back to look (default: 30 days)
    - limit: Max results per page (default: 20, max: 100)
    - offset: Pagination offset (default: 0)

    **Returns**:
        InsightsListResponse with array of insights, total count, and has_more flag
    """
    try:
        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Build base query
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        conditions = [
            AIInsight.portfolio_id == portfolio_id,
            AIInsight.created_at >= cutoff_date,
            AIInsight.dismissed == False  # Exclude dismissed insights
        ]

        # Add insight type filter if provided
        if insight_type:
            try:
                insight_type_enum = InsightType(insight_type)
                conditions.append(AIInsight.insight_type == insight_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid insight_type: {insight_type}"
                )

        # Get total count
        count_stmt = select(func.count(AIInsight.id)).where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()

        # Get insights with pagination
        insights_stmt = (
            select(AIInsight)
            .where(and_(*conditions))
            .order_by(desc(AIInsight.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(insights_stmt)
        insights = result.scalars().all()

        # Build response
        insight_responses = []
        for insight in insights:
            insight_responses.append(AIInsightResponse(
                id=str(insight.id),
                portfolio_id=str(insight.portfolio_id),
                insight_type=insight.insight_type.value,
                title=insight.title,
                severity=insight.severity.value,
                summary=insight.summary,
                key_findings=insight.key_findings or [],
                recommendations=insight.recommendations or [],
                full_analysis=insight.full_analysis or "",
                data_limitations=insight.data_limitations or "",
                focus_area=insight.focus_area,
                user_question=insight.user_question,
                created_at=insight.created_at.isoformat(),
                viewed=insight.viewed,
                dismissed=insight.dismissed,
                user_rating=float(insight.user_rating) if insight.user_rating else None,
                user_feedback=insight.user_feedback,
                performance=InsightPerformance(
                    cost_usd=float(insight.cost_usd) if insight.cost_usd else 0.0,
                    generation_time_ms=insight.generation_time_ms or 0,
                    token_count=insight.token_count or 0
                )
            ))

        return InsightsListResponse(
            insights=insight_responses,
            total=total,
            has_more=(offset + limit) < total
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error listing insights"
        )


@router.get("/{insight_id}", response_model=AIInsightResponse)
async def get_insight(
    insight_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single insight by ID.

    **Automatically marks insight as viewed** when fetched.

    **Returns**:
        AIInsightResponse with full insight details
    """
    try:
        # Fetch insight
        stmt = select(AIInsight).where(AIInsight.id == insight_id)
        result = await db.execute(stmt)
        insight = result.scalar_one_or_none()

        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight {insight_id} not found"
            )

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, insight.portfolio_id, current_user.id)

        # Mark as viewed if not already
        if not insight.viewed:
            insight.viewed = True
            await db.commit()
            await db.refresh(insight)

        # Build response
        return AIInsightResponse(
            id=str(insight.id),
            portfolio_id=str(insight.portfolio_id),
            insight_type=insight.insight_type.value,
            title=insight.title,
            severity=insight.severity.value,
            summary=insight.summary,
            key_findings=insight.key_findings or [],
            recommendations=insight.recommendations or [],
            full_analysis=insight.full_analysis or "",
            data_limitations=insight.data_limitations or "",
            focus_area=insight.focus_area,
            user_question=insight.user_question,
            created_at=insight.created_at.isoformat(),
            viewed=insight.viewed,
            dismissed=insight.dismissed,
            user_rating=float(insight.user_rating) if insight.user_rating else None,
            user_feedback=insight.user_feedback,
            performance=InsightPerformance(
                cost_usd=float(insight.cost_usd) if insight.cost_usd else 0.0,
                generation_time_ms=insight.generation_time_ms or 0,
                token_count=insight.token_count or 0
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching insight: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching insight"
        )


@router.patch("/{insight_id}", response_model=AIInsightResponse)
async def update_insight(
    insight_id: UUID,
    request: UpdateInsightRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update insight metadata (viewed, dismissed flags).

    **Use Cases**:
    - Mark as viewed when user opens detail view
    - Mark as dismissed to hide from list

    **Returns**:
        AIInsightResponse with updated insight
    """
    try:
        # Fetch insight
        stmt = select(AIInsight).where(AIInsight.id == insight_id)
        result = await db.execute(stmt)
        insight = result.scalar_one_or_none()

        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight {insight_id} not found"
            )

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, insight.portfolio_id, current_user.id)

        # Update fields
        if request.viewed is not None:
            insight.viewed = request.viewed

        if request.dismissed is not None:
            insight.dismissed = request.dismissed

        await db.commit()
        await db.refresh(insight)

        # Build response
        return AIInsightResponse(
            id=str(insight.id),
            portfolio_id=str(insight.portfolio_id),
            insight_type=insight.insight_type.value,
            title=insight.title,
            severity=insight.severity.value,
            summary=insight.summary,
            key_findings=insight.key_findings or [],
            recommendations=insight.recommendations or [],
            full_analysis=insight.full_analysis or "",
            data_limitations=insight.data_limitations or "",
            focus_area=insight.focus_area,
            user_question=insight.user_question,
            created_at=insight.created_at.isoformat(),
            viewed=insight.viewed,
            dismissed=insight.dismissed,
            user_rating=float(insight.user_rating) if insight.user_rating else None,
            user_feedback=insight.user_feedback,
            performance=InsightPerformance(
                cost_usd=float(insight.cost_usd) if insight.cost_usd else 0.0,
                generation_time_ms=insight.generation_time_ms or 0,
                token_count=insight.token_count or 0
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating insight: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error updating insight"
        )


@router.post("/{insight_id}/feedback", response_model=MessageResponse)
async def submit_feedback(
    insight_id: UUID,
    request: InsightFeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit user feedback/rating for an insight.

    **Feedback Types**:
    - Rating: 1-5 stars (required)
    - Text feedback: Optional comments

    **Returns**:
        MessageResponse confirming feedback submission
    """
    try:
        # Fetch insight
        stmt = select(AIInsight).where(AIInsight.id == insight_id)
        result = await db.execute(stmt)
        insight = result.scalar_one_or_none()

        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight {insight_id} not found"
            )

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, insight.portfolio_id, current_user.id)

        # Update feedback
        insight.user_rating = request.rating
        if request.feedback:
            insight.user_feedback = request.feedback

        await db.commit()

        logger.info(f"Feedback submitted for insight {insight_id}: rating={request.rating}")

        return MessageResponse(message="Feedback submitted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error submitting feedback"
        )
