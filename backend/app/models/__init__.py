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
from app.models.strategies import Strategy, StrategyLeg, StrategyMetrics, StrategyTag, StrategyType
from app.models.tags_v2 import TagV2

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

    # Strategies module
    "Strategy",
    "StrategyLeg",
    "StrategyMetrics",
    "StrategyTag",
    "StrategyType",

    # Tags v2 module
    "TagV2",
]
