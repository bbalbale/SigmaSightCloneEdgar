"""
SQLAlchemy models for SigmaSight Backend
"""

# Import all models to ensure they are registered with SQLAlchemy
from app.models.users import User, Portfolio
from app.models.positions import Position, Tag, PositionType, TagType, position_tags
from app.models.market_data import MarketDataCache, PositionGreeks, FactorDefinition, FactorExposure, PositionFactorExposure, FundHoldings
from app.models.snapshots import PortfolioSnapshot, BatchJob, BatchJobSchedule
from app.models.modeling import ModelingSessionSnapshot
from app.models.history import ExportHistory
from app.models.correlations import CorrelationCalculation, CorrelationCluster, CorrelationClusterPosition, PairwiseCorrelation
from app.models.target_prices import TargetPrice

# Export all models
__all__ = [
    # Users module
    "User",
    "Portfolio",
    
    # Positions module
    "Position",
    "Tag",
    "PositionType",
    "TagType",
    "position_tags",
    
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
]