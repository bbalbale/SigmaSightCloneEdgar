"""
AI Insights Models - Portfolio Analytical Reasoning System

Stores AI-generated portfolio analysis and investigation results.
"""
from sqlalchemy import Column, String, Text, DateTime, Numeric, Boolean, Enum as SQLEnum, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class InsightType(str, enum.Enum):
    """Types of AI-generated insights"""
    DAILY_SUMMARY = "daily_summary"
    VOLATILITY_ANALYSIS = "volatility_analysis"
    CONCENTRATION_RISK = "concentration_risk"
    HEDGE_QUALITY = "hedge_quality"
    FACTOR_EXPOSURE = "factor_exposure"
    STRESS_TEST_REVIEW = "stress_test_review"
    CUSTOM = "custom"


class InsightSeverity(str, enum.Enum):
    """Severity level of findings"""
    INFO = "info"
    NORMAL = "normal"
    ELEVATED = "elevated"
    WARNING = "warning"
    CRITICAL = "critical"


class DataQualityLevel(str, enum.Enum):
    """Data quality assessment"""
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"
    UNRELIABLE = "unreliable"


class AIInsight(Base):
    """
    Stores AI-generated portfolio analysis and insights.

    Represents output from the Analytical Reasoning Layer's investigations.
    """
    __tablename__ = "ai_insights"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)

    # Insight metadata
    insight_type = Column(SQLEnum(InsightType, name='insight_type', values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    severity = Column(SQLEnum(InsightSeverity, name='insight_severity', values_callable=lambda x: [e.value for e in x]), nullable=False, default=InsightSeverity.NORMAL)

    # Content
    summary = Column(Text, nullable=False)  # Short summary (2-3 sentences)
    full_analysis = Column(Text)  # Full markdown analysis
    key_findings = Column(JSON)  # List of key findings
    recommendations = Column(JSON)  # List of specific recommendations
    data_limitations = Column(Text)  # Transparency about incomplete/unreliable data

    # Investigation context
    context_data = Column(JSON)  # Snapshot of data used for analysis
    data_quality = Column(JSON)  # Quality assessment per metric {"volatility": "complete", ...}
    focus_area = Column(String(100))  # For focused investigations (e.g., "volatility")
    user_question = Column(Text)  # Optional user question for on-demand analysis

    # AI model information
    model_used = Column(String(50), nullable=False)  # e.g., "claude-sonnet-4"
    provider = Column(String(20), nullable=False, default="anthropic")  # "anthropic" or "openai"
    prompt_version = Column(String(20))  # Track prompt template version

    # Performance metrics
    cost_usd = Column(Numeric(10, 6))  # Cost in USD
    generation_time_ms = Column(Numeric(10, 2))  # Generation time in milliseconds
    token_count_input = Column(Numeric(10, 0))  # Input tokens
    token_count_output = Column(Numeric(10, 0))  # Output tokens
    tool_calls_count = Column(Numeric(3, 0), default=0)  # Number of analytical tools called

    # Caching
    cache_hit = Column(Boolean, default=False)  # Whether this was a cache hit
    cache_source_id = Column(UUID(as_uuid=True), ForeignKey("ai_insights.id"), nullable=True)  # If cached, source insight
    cache_key = Column(String(64), index=True)  # Cache key for similarity matching

    # User interaction
    user_rating = Column(Numeric(2, 1))  # 1-5 stars
    user_feedback = Column(Text)  # User comments
    viewed = Column(Boolean, default=False)  # Whether user has viewed
    dismissed = Column(Boolean, default=False)  # Whether user dismissed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime)  # Cache expiration
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="ai_insights")
    cache_source = relationship("AIInsight", remote_side=[id], foreign_keys=[cache_source_id])

    # Indexes for common queries
    __table_args__ = (
        Index('ix_ai_insights_portfolio_created', 'portfolio_id', 'created_at'),
        Index('ix_ai_insights_type_severity', 'insight_type', 'severity'),
        Index('ix_ai_insights_cache_lookup', 'cache_key', 'created_at'),
    )

    def __repr__(self):
        return f"<AIInsight {self.id} - {self.insight_type.value} - {self.title[:50]}>"


class AIInsightTemplate(Base):
    """
    Stores prompt templates for different insight types.

    Allows versioning and A/B testing of prompts.
    """
    __tablename__ = "ai_insight_templates"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template metadata
    insight_type = Column(SQLEnum(InsightType, name='insight_type', values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    version = Column(String(20), nullable=False)  # Semantic versioning e.g., "1.0.0"

    # Prompt templates (Jinja2 format)
    system_prompt = Column(Text, nullable=False)  # System-level instructions
    investigation_prompt = Column(Text, nullable=False)  # Investigation instructions

    # Configuration
    model_preference = Column(String(50))  # Preferred model (e.g., "claude-sonnet-4")
    max_tokens = Column(Numeric(6, 0))  # Token limit
    temperature = Column(Numeric(3, 2))  # Model temperature

    # Tools configuration
    required_tools = Column(JSON)  # List of required analytical tools
    optional_tools = Column(JSON)  # List of optional analytical tools

    # Quality metrics
    active = Column(Boolean, default=True, nullable=False)  # Is this template active?
    avg_quality_score = Column(Numeric(3, 2))  # Average user rating (1-5)
    usage_count = Column(Numeric(10, 0), default=0)  # Times used

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deprecated_at = Column(DateTime)  # When template was deprecated

    # Indexes
    __table_args__ = (
        Index('ix_ai_templates_type_active', 'insight_type', 'active'),
        Index('ix_ai_templates_version', 'insight_type', 'version'),
    )

    def __repr__(self):
        return f"<AIInsightTemplate {self.insight_type.value} v{self.version} - {self.name}>"
