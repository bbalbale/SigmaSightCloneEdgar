"""
Pydantic schemas for SigmaSight Backend

This package contains the Pydantic models used for data validation,
serialization, and API documentation.
"""

from .base import BaseSchema, TimestampedSchema
from .modeling import (
    ModelingSessionCreate,
    ModelingSessionUpdate,
    ModelingSessionInDB,
    ModelingSessionResponse,
    ModelingSessionListResponse
)
from .equity_change_schemas import (
    EquityChangeCreateRequest,
    EquityChangeUpdateRequest,
    EquityChangeResponse,
    EquityChangeListResponse,
    EquityChangeSummaryResponse,
    EquityChangeSummaryPeriod,
    EquityChangeExportRequest,
)
from .history import (
    ExportHistoryCreate,
    ExportHistoryInDB,
    ExportHistoryResponse
)
from .factors import (
    FactorDefinitionCreate,
    FactorDefinitionUpdate,
    FactorDefinitionInDB,
    FactorDefinitionResponse,
    FactorExposureCreate,
    FactorExposureInDB,
    FactorExposureResponse,
    PositionFactorExposureCreate,
    PositionFactorExposureInDB,
    PositionFactorExposureResponse
)
from .correlations import (
    PositionFilterConfig,
    CorrelationCalculationCreate,
    CorrelationCalculationUpdate,
    CorrelationCalculationResponse,
    ClusterPositionResponse,
    CorrelationClusterResponse,
    PairwiseCorrelationCreate,
    PairwiseCorrelationResponse,
    CorrelationMatrixResponse,
    PortfolioCorrelationMetricsResponse,
    CalculateCorrelationRequest,
    CorrelationMatrixRequest
)

__all__ = [
    # Base schemas
    "BaseSchema",
    "TimestampedSchema",
    
    # Modeling schemas
    "ModelingSessionCreate",
    "ModelingSessionUpdate",
    "ModelingSessionInDB",
    "ModelingSessionResponse",
    "ModelingSessionListResponse",

    # Equity change schemas
    "EquityChangeCreateRequest",
    "EquityChangeUpdateRequest",
    "EquityChangeResponse",
    "EquityChangeListResponse",
    "EquityChangeSummaryResponse",
    "EquityChangeSummaryPeriod",
    "EquityChangeExportRequest",

    # History schemas
    "ExportHistoryCreate",
    "ExportHistoryInDB",
    "ExportHistoryResponse",
    
    # Factor schemas
    "FactorDefinitionCreate",
    "FactorDefinitionUpdate",
    "FactorDefinitionInDB",
    "FactorDefinitionResponse",
    "FactorExposureCreate",
    "FactorExposureInDB",
    "FactorExposureResponse",
    "PositionFactorExposureCreate",
    "PositionFactorExposureInDB",
    "PositionFactorExposureResponse",
    
    # Correlation schemas
    "PositionFilterConfig",
    "CorrelationCalculationCreate",
    "CorrelationCalculationUpdate",
    "CorrelationCalculationResponse",
    "ClusterPositionResponse",
    "CorrelationClusterResponse",
    "PairwiseCorrelationCreate",
    "PairwiseCorrelationResponse",
    "CorrelationMatrixResponse",
    "PortfolioCorrelationMetricsResponse",
    "CalculateCorrelationRequest",
    "CorrelationMatrixRequest",
]
