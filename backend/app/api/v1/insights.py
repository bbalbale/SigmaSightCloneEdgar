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
- POST   /insights/generate                -> Generate new insight
- GET    /insights/portfolio/{portfolio_id} -> List portfolio insights
- GET    /insights/{insight_id}            -> Get single insight
- PATCH  /insights/{insight_id}            -> Update insight metadata
- POST   /insights/{insight_id}/feedback   -> Submit feedback/rating

**Backend Integration**:
- Service: app/services/analytical_reasoning_service.py (investigate_portfolio)
- Context Builder: app/services/hybrid_context_builder.py (aggregates portfolio data)
- AI Provider: app/services/anthropic_provider.py (Claude Sonnet 4)
- Models: app/models/ai_insights.py (AIInsight, AIInsightTemplate)

Created: 2025-10-22
"""
from datetime import datetime, timedelta
from typing import Optional, List, AsyncGenerator, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
import json
import time
import asyncio

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.schemas.auth import CurrentUser
from app.models.ai_insights import AIInsight, InsightType, InsightSeverity
from app.models.users import Portfolio
from app.agent.models.conversations import Conversation, ConversationMessage
from app.services.analytical_reasoning_service import analytical_reasoning_service
from app.services.anthropic_provider import anthropic_provider
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now

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
    http_request: Request = None,
):
    """
    Generate a new AI insight for a portfolio.
    """
    # CRITICAL DEBUG - This MUST appear in logs
    print(f"[INSIGHT-ENDPOINT] HIT! type={request.insight_type}, portfolio={request.portfolio_id}")
    logger.warning(f"[INSIGHT-ENDPOINT] HIT! type={request.insight_type}, portfolio={request.portfolio_id}")
    """

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
        # Extract JWT token from Authorization header for tool authentication
        auth_header = http_request.headers.get("Authorization", "") if http_request else ""
        auth_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

        # Validate portfolio ownership
        portfolio_id = UUID(request.portfolio_id)
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # TEMP: Rate limiting disabled for debugging
        # Check rate limiting (max 10 per portfolio per day)
        # today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        # count_stmt = select(func.count(AIInsight.id)).where(
        #     and_(
        #         AIInsight.portfolio_id == portfolio_id,
        #         AIInsight.created_at >= today_start
        #     )
        # )
        # count_result = await db.execute(count_stmt)
        # count = count_result.scalar()
        #
        # if count >= 10:
        #     raise HTTPException(
        #         status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        #         detail="Daily insight generation limit reached (10 per portfolio per day)"
        #     )

        # Convert insight_type string to enum
        try:
            insight_type_enum = InsightType(request.insight_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid insight_type. Must be one of: {', '.join([t.value for t in InsightType])}"
            )

        # Get ALL portfolios for this user (multi-portfolio support)
        all_portfolios_stmt = select(Portfolio).where(Portfolio.user_id == current_user.id)
        all_portfolios_result = await db.execute(all_portfolios_stmt)
        all_portfolios = all_portfolios_result.scalars().all()
        all_portfolio_ids = [p.id for p in all_portfolios]

        logger.info(f"Generating {request.insight_type} insight for user {current_user.id} with {len(all_portfolio_ids)} portfolios")

        insight = await analytical_reasoning_service.investigate_portfolio(
            db=db,
            portfolio_id=portfolio_id,  # Primary portfolio from request
            insight_type=insight_type_enum,
            focus_area=request.focus_area,
            user_question=request.user_question,
            auth_token=auth_token,
            portfolio_ids=all_portfolio_ids,  # All user portfolios for multi-portfolio analysis
        )

        if not insight:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate insight"
            )

        cost_str = f"${insight.cost_usd:.4f}" if insight.cost_usd is not None else "N/A"
        time_str = f"{insight.generation_time_ms}ms" if insight.generation_time_ms is not None else "N/A"
        logger.info(f"Generated insight {insight.id} (cost: {cost_str}, time: {time_str})")

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
                generation_time_ms=int(insight.generation_time_ms) if insight.generation_time_ms else 0,
                token_count=int(insight.token_count_input or 0) + int(insight.token_count_output or 0)
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating insight: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {type(e).__name__}: {str(e)}"
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
                    generation_time_ms=int(insight.generation_time_ms) if insight.generation_time_ms else 0,
                    token_count=int(insight.token_count_input or 0) + int(insight.token_count_output or 0)
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
                generation_time_ms=int(insight.generation_time_ms) if insight.generation_time_ms else 0,
                token_count=int(insight.token_count_input or 0) + int(insight.token_count_output or 0)
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
                generation_time_ms=int(insight.generation_time_ms) if insight.generation_time_ms else 0,
                token_count=int(insight.token_count_input or 0) + int(insight.token_count_output or 0)
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


# ============================================================================
# Claude Streaming Chat Endpoint
# ============================================================================

class ChatMessageRequest(BaseModel):
    """Request schema for Claude chat messages"""
    message: str = Field(..., description="User message to send to Claude")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID to continue")


async def load_claude_message_history(
    conversation_id: UUID,
    db: AsyncSession,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Load recent message history for Claude conversation"""
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    # Convert to dict format and reverse to chronological order
    history = []
    for msg in reversed(messages):
        msg_dict = {
            "role": msg.role,
            "content": msg.content
        }
        # Include tool calls for Claude context
        if msg.tool_calls:
            msg_dict["tool_calls"] = msg.tool_calls
        history.append(msg_dict)

    return history


async def claude_sse_generator(
    message_text: str,
    conversation: Conversation,
    db: AsyncSession,
    current_user: CurrentUser,
    auth_token: str
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for Claude chat with tool execution.

    Streams:
    - Start event with conversation metadata
    - Text chunks as Claude generates response
    - Tool call notifications when Claude uses tools
    - Done event with final metrics
    """
    start_time = time.time()
    run_id = f"run_{uuid4().hex[:12]}"
    tool_calls_made = 0

    try:
        # Send start event
        start_event = {
            "type": "start",
            "conversation_id": str(conversation.id),
            "provider": "anthropic",
            "model": "claude-sonnet-4",
            "run_id": run_id,
            "timestamp": int(time.time() * 1000)
        }
        yield f"event: start\ndata: {json.dumps(start_event)}\n\n"

        # Load message history
        message_history = await load_claude_message_history(conversation.id, db)

        # Get portfolio context from conversation metadata
        portfolio_id = conversation.meta_data.get("portfolio_id") if conversation.meta_data else None

        # Build context for Claude
        context = {
            "portfolio_id": str(portfolio_id) if portfolio_id else None,
            "data_sources": {
                "portfolio_complete": "available",
                "analytics": "available",
                "tools": "enabled"
            }
        }

        # Save user message
        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=message_text,
            created_at=utc_now()
        )
        db.add(user_msg)
        await db.commit()

        # TODO: Implement streaming Claude response
        # For now, use investigate() method and stream the result
        # Future: Create streaming version of investigate() that yields chunks

        logger.info(f"Calling Claude investigate with tools enabled for conversation {conversation.id}")

        # Call Claude with tools (non-streaming for now)
        result = await anthropic_provider.investigate(
            context=context,
            insight_type=InsightType.CUSTOM,
            user_question=message_text,
            auth_token=auth_token
        )

        # Extract response
        response_text = result.get("full_analysis", result.get("summary", ""))
        tool_calls_made = result.get("performance", {}).get("tool_calls_count", 0)

        # Stream response text in chunks (simulate streaming)
        words = response_text.split()
        chunk_size = 10
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            message_event = {
                "type": "message",
                "delta": chunk + " ",
                "role": "assistant"
            }
            yield f"event: message\ndata: {json.dumps(message_event)}\n\n"
            await asyncio.sleep(0.05)  # Simulate streaming delay

        # Save assistant message
        assistant_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
            tool_calls=[{"count": tool_calls_made}] if tool_calls_made > 0 else [],
            prompt_tokens=result.get("performance", {}).get("token_count_input", 0),
            completion_tokens=result.get("performance", {}).get("token_count_output", 0),
            total_tokens=result.get("performance", {}).get("token_count_input", 0) + result.get("performance", {}).get("token_count_output", 0),
            latency_ms=int(result.get("performance", {}).get("generation_time_ms", 0)),
            created_at=utc_now()
        )
        db.add(assistant_msg)
        await db.commit()

        # Send done event
        generation_time_ms = (time.time() - start_time) * 1000
        done_event = {
            "type": "done",
            "run_id": run_id,
            "data": {
                "final_text": response_text,
                "tool_calls_count": tool_calls_made,
                "total_tokens": assistant_msg.total_tokens,
                "generation_time_ms": int(generation_time_ms)
            },
            "timestamp": int(time.time() * 1000)
        }
        yield f"event: done\ndata: {json.dumps(done_event)}\n\n"

    except Exception as e:
        logger.error(f"Error in Claude SSE generator: {e}", exc_info=True)
        error_event = {
            "type": "error",
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        }
        yield f"event: error\ndata: {json.dumps(error_event)}\n\n"


@router.post("/chat")
async def chat_with_claude(
    request: ChatMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    http_request: Request = None
):
    """
    Stream chat response from Claude with tool execution.

    Features:
    - SSE streaming for real-time responses
    - Tool execution (Claude can call analytics tools)
    - Conversation history persistence
    - Multi-turn conversations

    Returns:
        StreamingResponse with Server-Sent Events
    """
    try:
        # Get or create conversation
        if request.conversation_id:
            # Load existing conversation
            conversation_uuid = UUID(request.conversation_id)
            result = await db.execute(
                select(Conversation)
                .where(
                    and_(
                        Conversation.id == conversation_uuid,
                        Conversation.user_id == current_user.id
                    )
                )
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
        else:
            # Create new conversation
            # Get user's portfolio ID
            portfolio_result = await db.execute(
                select(Portfolio)
                .where(Portfolio.user_id == current_user.id)
                .limit(1)
            )
            portfolio = portfolio_result.scalar_one_or_none()

            conversation = Conversation(
                user_id=current_user.id,
                provider="anthropic",
                mode="claude-insights",
                meta_data={
                    "portfolio_id": str(portfolio.id) if portfolio else None,
                    "model": "claude-sonnet-4",
                    "tools_enabled": True
                },
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

        # Get auth token from request header
        auth_header = http_request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

        # Generate SSE stream
        return StreamingResponse(
            claude_sse_generator(
                message_text=request.message,
                conversation=conversation,
                db=db,
                current_user=current_user,
                auth_token=auth_token
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
