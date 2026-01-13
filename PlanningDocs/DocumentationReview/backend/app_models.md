# App Models Directory Documentation

This document describes all files in `backend/app/models/`.

---

## Overview

The `app/models/` directory contains 19 SQLAlchemy ORM model files defining the database schema for SigmaSight's dual PostgreSQL database architecture. Models are split between the Core database (gondola) and AI database (metro) for production Railway deployment.

---

## Core User & Portfolio Models

### `users.py`
Defines `User` (with Clerk authentication, AI message quota, tier management) and `Portfolio` (portfolio container with soft-delete). Used by authentication, portfolio operations, batch processing, and chat.

### `positions.py`
Defines `Position` (individual holdings), `PositionType` enum (LONG, SHORT, LC, LP, SC, SP), and legacy Tag model. Used by position management, P&L calculations, Greeks, tagging, and analytics.

---

## Market Data & Analytics Models

### `market_data.py`
Defines 15+ models: `MarketDataCache` (historical prices), `CompanyProfile` (53 fields), `PositionGreeks`, `FactorDefinition`, `FactorExposure`, `PositionFactorExposure`, `PositionMarketBeta`, `BenchmarkSectorWeight`, `MarketRiskScenario`, `PositionInterestRateBeta`, `PositionVolatility`, `StressTestScenario`, `StressTestResult`, `FactorCorrelation`, `FundHoldings`. Used by market data collection, analytics API, Greeks, factors, and batch processing.

### `snapshots.py`
Defines `PortfolioSnapshot` (daily portfolio state), `BatchJob` (execution history), `BatchJobSchedule` (cron definitions). Used by snapshot creation, analytics queries, and batch scheduling.

### `correlations.py`
Defines `CorrelationCalculation`, `CorrelationCluster`, `CorrelationClusterPosition`, `PairwiseCorrelation` for position correlation tracking. Used by correlation calculations and analytics.

---

## Tagging & Target Price Models

### `tags_v2.py`
Defines `TagV2` - enhanced user-scoped tags with color, description, archiving, usage tracking (October 2, 2025). Used by tag management API and position tagging.

### `position_tags.py`
Defines `PositionTag` - M:N junction table linking Position ↔ TagV2. Used by position tagging API and tag service.

### `target_prices.py`
Defines `TargetPrice` - position target prices with upside/downside scenarios (Phase 8). Used by target price API and portfolio analytics.

---

## Financial Data Models

### `fundamentals.py`
Defines `IncomeStatement`, `BalanceSheet`, `CashFlow` - quarterly/annual financial statement data. Used by fundamentals service and valuation calculations.

### `equity_changes.py`
Defines `EquityChange` and `EquityChangeType` enum for capital contributions/withdrawals. Used by equity management API and P&L adjustments.

### `position_realized_events.py`
Defines `PositionRealizedEvent` for realized P&L events supporting partial closes. Used by P&L calculations and exit tracking.

---

## AI & Insights Models

### `ai_insights.py`
Defines `AIInsight` (AI analytical results with caching) and `AIInsightTemplate` (prompt templates) in Core DB. Used by insights API and agent system.

### `ai_models.py`
Defines AI database models using separate `AiBase`: `AIKBDocument` (RAG with pgvector), `AIMemory` (user preferences), `AIFeedback` (ratings), `AIAdminAnnotation` (tuning). Used by chat feedback, agent memory, and admin dashboard.

---

## Symbol & Admin Models

### `symbol_analytics.py`
Defines `SymbolUniverse`, `SymbolFactorExposure`, `SymbolDailyMetrics` for symbol-level analytics (December 2025). Used by factor calculations, symbol caching, and batch processing.

### `admin.py`
Defines `AdminUser`, `AdminSession`, `UserActivityEvent`, `AIRequestMetrics`, `BatchRunHistory`, `DailyMetrics` for admin and tracking (December 2025). Used by admin dashboard and monitoring.

---

## Supporting Models

### `history.py`
Defines `ExportHistory` for CSV/JSON/FIX export audit trail. Used by export operations.

### `modeling.py`
Defines `ModelingSessionSnapshot` for what-if analysis temporary states. Used by ProForma Analytics.

### `batch_tracking.py`
Defines `BatchRunTracking` for per-day batch status with phase metrics. Used by batch orchestrator and monitoring.

### `__init__.py`
Package initialization for models module. Used for central imports.

---

## Dual Database Architecture

**Core Database (gondola)**: User, Portfolio, Position, MarketData, Snapshots, Conversations, TargetPrices, Tags, AIInsight

**AI Database (metro)**: AIKBDocument, AIMemory, AIFeedback, AIAdminAnnotation (uses separate `AiBase`)

---

## Key Relationships

```
User → Portfolio (1:N)
Portfolio → Position (1:N)
Position → PositionGreeks (1:1, optional)
Position → PositionFactorExposure (1:N)
Position → PositionMarketBeta (1:N)
Position → TargetPrice (1:1, optional)
Position ← M:N → TagV2 (via PositionTag)
Portfolio → PortfolioSnapshot (1:N)
```

---

## Common Import Patterns

```python
# Core models
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.models.tags_v2 import TagV2
from app.models.position_tags import PositionTag
from app.models.target_prices import TargetPrice

# Analytics models
from app.models.market_data import (
    PositionGreeks, PositionFactorExposure,
    PositionMarketBeta, CompanyProfile, FactorDefinition
)
from app.models.snapshots import PortfolioSnapshot

# AI models (separate database)
from app.models.ai_models import AIKBDocument, AIMemory, AIFeedback
```

---

## Summary Statistics

- **Total Model Files**: 19 (plus __init__.py)
- **Total Models Defined**: 45+
- **Core Database Tables**: 30+
- **AI Database Tables**: 4
- **Enums**: 8+ (PositionType, EquityChangeType, etc.)
