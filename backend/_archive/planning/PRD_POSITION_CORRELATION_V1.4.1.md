# Position Correlation Analysis Feature PRD

## 1. Overall Intent

Implement comprehensive position correlation analysis providing investors with position-level correlation metrics, cluster risk identification, and detailed pairwise correlation matrices to understand concentration risks and diversification effectiveness across their holdings.

## 2. User Experience Definition

### Portfolio-Level Metrics Dashboard
- Display four key correlation metrics: overall portfolio correlation score, correlation concentration score, correlation cluster summary, and correlation duration selector
- Overall portfolio correlation score shows average pairwise correlation across all positions as single decimal value with risk level indicator
- Correlation concentration score shows percentage of portfolio trapped in high-correlation clusters
- Cluster summary displays each identified cluster with nickname, member positions, correlation strength, individual position values/percentages, and cluster totals
- Single duration calculation of 90 days optimized for computational efficiency and statistical reliability

### Pairwise PositionCorrelation Matrix
- Interactive correlation matrix showing all portfolio positions on both X and Y axes with correlation coefficients in grid cells
- Color-coded correlation strength visualization from negative correlation (blue) through neutral (white) to high positive correlation (red)
- Multiple filtering capabilities: correlation threshold slider, position type filters (long/short/options), dollar exposure filters, and delta-adjusted exposure filters
- Fixed 90-day correlation period for optimal balance of statistical significance and computational performance
- Export functionality for correlation data

## 3. API Endpoint Definition

### GET /api/v1/risk/correlations/positions/metrics
**Purpose**: Retrieve portfolio-level correlation metrics
**Query Parameters**:
- `min_position_value`: Optional float, minimum absolute position value for inclusion (default: $10,000)
- `min_portfolio_weight`: Optional float, minimum portfolio weight for inclusion (default: 0.01)
- `filter_mode`: Optional string ("value_only", "weight_only", "both", "either"), defaults to "both"
- `correlation_threshold`: Optional float (0.0 to 1.0), correlation threshold for cluster detection (default: 0.7)
- `view`: Optional string ("portfolio", "longs", "shorts"), defaults to "portfolio"

**Response Schema**:
```json
{
  "overall_correlation": 0.45,
  "correlation_concentration_score": 0.23,
  "effective_positions": 12.3,
  "clusters": [
    {
      "id": "cluster_1",
      "nickname": "Big Tech",
      "avg_correlation": 0.83,
      "positions": [
        {
          "symbol": "AAPL",
          "value": 50000.00,
          "portfolio_percentage": 0.05,
          "correlation_to_cluster": 0.81
        }
      ],
      "total_value": 250000.00,
      "portfolio_percentage": 0.25
    }
  ],
  "calculation_date": "2025-01-15",
  "duration_days": 90,
  "position_filters": {
    "min_position_value": 10000.00,
    "min_portfolio_weight": 0.01,
    "positions_included": 45,
    "positions_filtered": 12
  },
  "data_quality": "sufficient"
}
```

### GET /api/v1/risk/correlations/positions/matrix
**Purpose**: Retrieve full pairwise correlation matrix
**Query Parameters**:
- `min_position_value`: Optional float, minimum absolute position value for inclusion (default: $10,000)
- `min_portfolio_weight`: Optional float, minimum portfolio weight for inclusion (default: 0.01)
- `min_correlation`: Optional float (-1.0 to 1.0), filters correlations by minimum threshold
- `max_correlation`: Optional float (-1.0 to 1.0), filters correlations by maximum threshold
- `position_types`: Optional array of strings ("LONG", "SHORT", "LC", "LP", "SC", "SP")
- `min_dollar_exposure`: Optional float, minimum absolute dollar exposure
- `min_delta_exposure`: Optional float, minimum absolute delta-adjusted exposure
- `view`: Optional string ("portfolio", "longs", "shorts"), defaults to "portfolio"

**Response Schema**:
```json
{
  "correlation_matrix": {
    "symbols": ["AAPL", "MSFT", "GOOGL"],
    "correlations": [
      [1.0, 0.82, 0.75],
      [0.82, 1.0, 0.79],
      [0.75, 0.79, 1.0]
    ]
  },
  "position_metadata": [
    {
      "symbol": "AAPL",
      "position_type": "LONG",
      "dollar_exposure": 50000.00,
      "delta_adjusted_exposure": 50000.00,
      "data_points": 58
    }
  ],
  "calculation_date": "2025-01-15",
  "duration_days": 90,
  "position_filters": {
    "min_position_value": 10000.00,
    "min_portfolio_weight": 0.01,
    "positions_included": 45,
    "positions_filtered": 12
  },
  "filters_applied": {
    "min_correlation": null,
    "position_types": ["LONG", "SHORT"],
    "min_dollar_exposure": null
  }
}
```

### POST /api/v1/risk/correlations/positions/calculate
**Purpose**: Trigger correlation calculation for specific portfolio with position filtering
**Request Body**:
```json
{
  "portfolio_id": "uuid",
  "duration_days": 90,
  "position_filters": {
    "min_position_value": 10000.00,
    "min_portfolio_weight": 0.01,
    "filter_mode": "both",
    "correlation_threshold": 0.7
  },
  "force_recalculate": false
}
```

## 4. Technical Design

### Database Schema Extensions

**New Table: correlation_calculations**
```sql
CREATE TABLE correlation_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    duration_days INTEGER NOT NULL,
    calculation_date DATE NOT NULL,
    overall_correlation DECIMAL(8,6) NOT NULL,
    correlation_concentration_score DECIMAL(8,6) NOT NULL,
    effective_positions DECIMAL(8,2) NOT NULL,
    data_quality VARCHAR(20) NOT NULL,
    -- Position filtering configuration (stored per-portfolio)
    min_position_value DECIMAL(18,4),
    min_portfolio_weight DECIMAL(8,6),
    filter_mode VARCHAR(20) DEFAULT 'both', -- 'value_only', 'weight_only', 'both', 'either'
    correlation_threshold DECIMAL(8,6) DEFAULT 0.7,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(portfolio_id, duration_days, calculation_date)
);
```

**New Table: correlation_clusters**
```sql
CREATE TABLE correlation_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_calculation_id UUID NOT NULL REFERENCES correlation_calculations(id),
    cluster_number INTEGER NOT NULL,
    nickname VARCHAR(100) NOT NULL,
    avg_correlation DECIMAL(8,6) NOT NULL,
    total_value DECIMAL(18,4) NOT NULL,
    portfolio_percentage DECIMAL(8,6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**New Table: correlation_cluster_positions**
```sql
CREATE TABLE correlation_cluster_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID NOT NULL REFERENCES correlation_clusters(id),
    position_id UUID NOT NULL REFERENCES positions(id),
    symbol VARCHAR(20) NOT NULL,
    value DECIMAL(18,4) NOT NULL,
    portfolio_percentage DECIMAL(8,6) NOT NULL,
    correlation_to_cluster DECIMAL(8,6) NOT NULL
);
```

**New Table: pairwise_correlations**
```sql
CREATE TABLE pairwise_correlations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_calculation_id UUID NOT NULL REFERENCES correlation_calculations(id),
    symbol_1 VARCHAR(20) NOT NULL,
    symbol_2 VARCHAR(20) NOT NULL,
    correlation_value DECIMAL(8,6) NOT NULL,
    data_points INTEGER NOT NULL,
    statistical_significance DECIMAL(8,6),
    INDEX(correlation_calculation_id, symbol_1, symbol_2)
);
```

### Service Layer Architecture

**New Service: CorrelationService**
- `calculate_portfolio_correlations(portfolio_id, min_position_value, min_portfolio_weight, filter_mode='both', correlation_threshold=0.7)`: Main calculation orchestrator with configurable position filtering
- `filter_significant_positions(positions, min_value, min_weight, filter_mode)`: Filter positions by value and/or weight thresholds based on filter_mode ('value_only', 'weight_only', 'both', 'either')
- `calculate_pairwise_correlations(returns_data)`: Compute full correlation matrix using pandas.DataFrame.corr() with log returns
- `detect_correlation_clusters(correlation_matrix, threshold=0.7)`: Identify position clusters using graph connectivity (configurable threshold)
- `calculate_portfolio_metrics(correlations, positions)`: Compute overall correlation and concentration scores
- `generate_cluster_nicknames(clusters, positions)`: Create human-readable cluster names using waterfall: tags → sector → largest position (e.g., "AAPL lookalikes")

**Enhanced Service: MarketDataService**
- `get_position_returns(significant_positions, start_date, end_date)`: Retrieve 90-day daily returns for filtered positions
- `validate_data_sufficiency(position_returns, min_days=20)`: Ensure adequate data for reliable correlations
- `get_significant_positions(portfolio_id, min_value, min_weight)`: Filter positions by value and weight criteria

### Batch Job Integration

**New Job: correlation_calculation_job.py**
- Runs weekly at 6:00 PM (Tuesday after factor calculations and risk metrics)
- Calculates single 90-day correlation matrix for each portfolio with position filtering
- Only includes positions meeting minimum value ($10K) and weight (1%) thresholds
- Implements incremental calculation strategy: only recalculate if significant positions changed
- Error handling for insufficient data scenarios with graceful degradation to smaller position sets
- Performance optimization using vectorized pandas operations for filtered position sets

### Calculation Engine Design

**Core Algorithm Flow**:
1. Filter portfolio positions based on configurable filter_mode:
   - 'value_only': Only apply minimum value threshold
   - 'weight_only': Only apply minimum weight threshold
   - 'both': Positions must meet BOTH thresholds (default)
   - 'either': Positions must meet at least ONE threshold
2. Fetch 90-day daily price data for filtered positions
3. Calculate log returns: ln(price_t / price_t-1)
4. Exclude positions with insufficient data points (<20 days)
5. Calculate full pairwise correlation matrix using Pearson correlation on log returns
6. Store full matrix including self-correlations (A,A) and both directions (A,B) and (B,A)
7. Identify correlation clusters using depth-first search on correlation graph (configurable threshold, default 0.7)
8. Generate cluster nicknames using waterfall logic:
   - Check if positions share common tags
   - Check if positions share common sector
   - Use largest position symbol + "lookalikes" (e.g., "AAPL lookalikes")
9. Calculate portfolio-level metrics: overall correlation, concentration score, effective positions
10. Store complete correlation matrix and metadata in database tables

**Performance Optimizations**:
- Position filtering reduces matrix size by ~90% (500 positions → 50 significant positions)
- Single 90-day calculation eliminates 75% of computational load vs multi-duration approach
- Use pandas vectorized operations for correlation calculations on filtered dataset
- Implement weekly correlation caching with 7-day TTL
- Batch database inserts for correlation matrices (storing full matrix for grid presentation)
- Minimum data validation (20 days) ensures statistical reliability

### API Layer Integration

**Enhanced Controller: RiskController**
- Add correlation endpoints to existing risk API structure
- Implement query parameter validation and filtering logic
- Add response caching using existing cache infrastructure
- Integrate with portfolio aggregation service for position data
- Error handling for missing correlation data with appropriate HTTP status codes

## 5. Todo List

### Database & Models (2 days)
- [ ] Create correlation_calculations table with proper indexes and constraints
- [ ] Create correlation_clusters table with foreign key relationships
- [ ] Create correlation_cluster_positions table with position references
- [ ] Create pairwise_correlations table with optimized indexes for matrix queries
- [ ] Add SQLAlchemy models for new correlation tables with proper relationships
- [ ] Create database migration scripts for new correlation schema
- [ ] Add database indexes for correlation query performance optimization

### Core Calculation Engine (2 days) - Optimized
- [ ] Implement CorrelationService.filter_significant_positions() with value/weight thresholds
- [ ] Implement CorrelationService.calculate_portfolio_correlations() with position filtering
- [ ] Implement CorrelationService.calculate_pairwise_correlations() using pandas.DataFrame.corr() for full matrix
- [ ] Implement CorrelationService.detect_correlation_clusters() with graph connectivity algorithm
- [ ] Implement CorrelationService.calculate_portfolio_metrics() for overall correlation and concentration scores
- [ ] Implement CorrelationService.generate_cluster_nicknames() with sector-based heuristics
- [ ] Add correlation data validation and quality scoring logic with 20-day minimum
- [ ] Implement error handling for insufficient data scenarios with graceful position set reduction

### Market Data Integration (1 day)
- [ ] Implement MarketDataService.get_significant_positions() with value/weight filtering
- [ ] Enhance MarketDataService.get_position_returns() for 90-day data retrieval on filtered positions
- [ ] Add MarketDataService.validate_data_sufficiency() with 20-day minimum requirement
- [ ] Integrate position filtering with existing market data pipeline
- [ ] Add return data caching for weekly correlation calculation performance

### Batch Job Implementation (1 day) - Optimized
- [ ] Create correlation_calculation_job.py with weekly execution schedule (Tuesday 6 PM)
- [ ] Implement single 90-day calculation logic with position filtering
- [ ] Add incremental calculation strategy with significant position change detection
- [ ] Integrate correlation job into existing batch job sequence after risk calculations
- [ ] Add job monitoring and error notification for correlation failures
- [ ] Implement performance optimization using position filtering and vectorized operations

### API Endpoints (2 days)
- [ ] Implement GET /api/v1/risk/correlations/positions/metrics with query parameter support
- [ ] Implement GET /api/v1/risk/correlations/positions/matrix with filtering capabilities
- [ ] Implement POST /api/v1/risk/correlations/positions/calculate for manual triggers
- [ ] Add comprehensive query parameter validation for all correlation endpoints
- [ ] Implement response filtering logic for correlation thresholds and exposure amounts
- [ ] Add correlation API response caching with appropriate TTL
- [ ] Integrate correlation endpoints with existing authentication and authorization

### Testing & Validation (2 days)
- [ ] Create unit tests for CorrelationService methods with mock data
- [ ] Create integration tests for correlation calculation with real portfolio data
- [ ] Add performance tests for correlation matrix calculation with large portfolios
- [ ] Create API endpoint tests for all correlation endpoints with various filter combinations
- [ ] Add correlation cluster detection tests with known correlation patterns
- [ ] Implement correlation calculation accuracy validation against known benchmarks
- [ ] Add batch job testing for correlation calculation pipeline

### Documentation & Monitoring (1 day)
- [ ] Add correlation calculation documentation to API specification
- [ ] Create correlation metrics monitoring and alerting for batch job failures
- [ ] Add correlation data quality monitoring with statistical validation
- [ ] Update project README with correlation feature documentation
- [ ] Create correlation troubleshooting guide for data quality issues

**Total Estimated Time: 10 days** (reduced from 13 days via computational optimizations)

## Computational Load Reduction Summary

**Optimization Impact:**
- **Position filtering**: 500 positions → ~50 significant positions = 99% reduction in matrix size
- **Single duration**: 4 durations → 1 duration (90d) = 75% reduction in calculations
- **Weekly schedule**: Daily → weekly execution = 85% reduction in batch job frequency
- **Combined effect**: ~99.8% reduction in total computational load

**Performance Comparison:**
- **Original**: 500² × 4 durations × 365 days = 365M calculations/year
- **Optimized**: 50² × 1 duration × 52 weeks = 130K calculations/year
- **Storage**: Full correlation matrices maintained for complete grid presentation
- **User experience**: Preserved full matrix visualization with significant performance gains