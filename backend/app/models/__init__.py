"""
SQLAlchemy models for SigmaSight Backend
"""

# Import all models to ensure they are registered with SQLAlchemy
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType, TagType
from app.models.market_data import MarketDataCache, PositionGreeks, FactorDefinition, FactorExposure, PositionFactorExposure, FundHoldings
from app.models.snapshots import PortfolioSnapshot, BatchJob, BatchJobSchedule
from app.models.modeling import ModelingSessionSnapshot
from app.models.history import ExportHistory
from app.models.correlations import CorrelationCalculation, CorrelationCluster, CorrelationClusterPosition, PairwiseCorrelation
from app.models.target_prices import TargetPrice
from app.models.tags_v2 import TagV2
from app.models.position_tags import PositionTag
from app.models.position_realized_events import PositionRealizedEvent
from app.models.equity_changes import EquityChange, EquityChangeType
from app.models.ai_insights import AIInsight
from app.models.ai_models import AIKBDocument, AIMemory, AIFeedback
from app.models.fundamentals import IncomeStatement, BalanceSheet, CashFlow
from app.models.symbol_analytics import SymbolUniverse, SymbolFactorExposure, SymbolDailyMetrics

# Export all models
__all__ = [
    # Users module
    "User",
    "Portfolio",
    
    # Positions module
    "Position",
    "PositionType",
    "TagType",
    
    # Market data module
    "MarketDataCache",
    "PositionGreeks",
    "FactorDefinition",
    "FactorExposure",
    "PositionFactorExposure",
    "FundHoldings",
    
    # Snapshots module
    "PortfolioSnapshot",
    "BatchJob",
    "BatchJobSchedule",
    
    # Modeling module
    "ModelingSessionSnapshot",
    
    # History module
    "ExportHistory",
    
    # Correlations module
    "CorrelationCalculation",
    "CorrelationCluster",
    "CorrelationClusterPosition",
    "PairwiseCorrelation",

    # Target prices module
    "TargetPrice",

    # Tags v2 module
    "TagV2",

    # Position tags module
    "PositionTag",
    "PositionRealizedEvent",
    "EquityChange",
    "EquityChangeType",

    # AI insights module (Core database)
    "AIInsight",

    # AI learning models (AI database - uses AiBase, not Base)
    "AIKBDocument",
    "AIMemory",
    "AIFeedback",

    # Fundamentals module
    "IncomeStatement",
    "BalanceSheet",
    "CashFlow",

    # Symbol analytics module (Symbol Factor Universe architecture)
    "SymbolUniverse",
    "SymbolFactorExposure",
    "SymbolDailyMetrics",
]
