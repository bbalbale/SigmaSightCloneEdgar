# Database Design Documentation

> ⚠️ **STATUS UPDATE (2025-08-26 15:05 PST)**: Database schema has been fully implemented with migrations. All tables are operational in production. See [AI_AGENT_REFERENCE.md](../../AI_AGENT_REFERENCE.md) for current schema and relationships.

Please be sure to consider DATABASE_DESIGN_ADDENDUM_V1.4.1.md which is an updated addendum.
## 1. Core Tables

### 1.1 Modeling Session Snapshots
```sql
CREATE TABLE modeling_session_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  base_snapshot_date DATE NOT NULL,
  
  -- Changes and impacts
  modifications JSONB NOT NULL, -- Detailed list of changes
  impact_summary JSONB NOT NULL, -- Summary of impacts
  
  -- Risk changes
  risk_metrics_before JSONB,
  risk_metrics_after JSONB,
  factor_exposures_change JSONB,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  created_by UUID REFERENCES users(id)
);
```

### 1.2 Export History
```sql
CREATE TABLE export_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  export_type VARCHAR(50) NOT NULL, -- 'portfolio', 'trades', 'modeling_session'
  export_format VARCHAR(20) NOT NULL, -- 'csv', 'json', 'fix'
  file_name VARCHAR(255),
  file_size_bytes INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 1.3 Modeling Session Snapshots
```sql
CREATE TABLE modeling_session_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id VARCHAR(50) UNIQUE NOT NULL, -- e.g., "session_789"
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL, -- e.g., "Tech Exposure Reduction"
  status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'completed', 'cancelled')),
  base_portfolio_snapshot JSONB NOT NULL, -- Original portfolio state
  modified_portfolio_snapshot JSONB, -- Current modified state
  changes JSONB, -- Array of change objects
  impact_summary JSONB, -- Calculated impact metrics
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Index for active sessions lookup
CREATE INDEX idx_modeling_sessions_user_status ON modeling_session_snapshots(user_id, status)
  WHERE status = 'active';
```

### 1.3 Calculation Audit Log
```sql
CREATE TABLE calculation_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  calculation_type VARCHAR(50) NOT NULL, -- 'greeks', 'factors', 'risk_metrics'
  portfolio_id UUID REFERENCES portfolios(id),
  calculation_date DATE NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  status VARCHAR(20) NOT NULL, -- 'running', 'completed', 'failed'
  records_processed INTEGER,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 2. Implementation Guide

### 2.1 Prerequisites
- PostgreSQL 14+ (for gen_random_uuid() function)
- TimescaleDB extension (optional, for time-series optimization)
- Environment variables for database connection

### 2.2 Database Setup Order

#### 2.2.1 Core Tables
1. Users and auth
2. Portfolios
3. Tags
4. Factor definitions
5. Stress scenarios

#### 2.2.2 Position Tables
6. Positions
7. Position relationships
8. Position attributes
9. Strategy groups

#### 2.2.3 Market Data Tables
10. Market data
11. Realtime quotes
12. Short selling metrics

#### 2.2.4 Analytics Tables
13. Greeks and factors
14. Portfolio analytics
15. Other analytics

#### 2.2.5 Supporting Tables
16. Modeling and export

## 3. Environment Configuration

```bash
# .env file
DATABASE_URL=postgresql://user:password@localhost:5432/sigmasight
POLYGON_API_KEY=your_polygon_api_key
REDIS_URL=redis://localhost:6379
```

## 4. Initial Data Seeding

### 4.1 Default Factors
```sql
INSERT INTO factor_definitions (name, display_name, category, sort_order) VALUES
('market_beta', 'Market Beta', 'style', 1),
('momentum', 'Momentum', 'style', 2),
('value', 'Value', 'style', 3),
('growth', 'Growth', 'style', 4),
('quality', 'Quality', 'style', 5),
('size', 'Size', 'style', 6),
('short_interest', 'Short Interest', 'technical', 7),
('volatility', 'Volatility', 'technical', 8);
```

### Default Stress Scenarios
```sql
INSERT INTO stress_scenarios (name, scenario_type, sort_order) VALUES
('Market Up 10%', 'sensitivity', 1),
('Market Down 10%', 'sensitivity', 2),
('Rates Up 0.25%', 'sensitivity', 3),
('Rates Down 0.25%', 'sensitivity', 4),
('Oil Up 5%', 'sensitivity', 5),
('Oil Down 5%', 'sensitivity', 6),
('2008 Financial Crisis', 'historical', 7),
('COVID-19 Crash', 'historical', 8);
```

### ~~4.3 Historical Market Data~~ *(REMOVED - V1.4 scope change)*
```sql
-- ~~After positions are loaded, populate with real historical data:~~
-- ~~1. Fetch from Polygon.io API~~
-- ~~2. Store in market_data_cache~~
-- ~~3. Generate portfolio_snapshots using actual prices~~

-- ~~Example of what gets stored (but with real data):~~
-- ~~INSERT INTO market_data_cache (ticker, date, open, high, low, close, volume, data_source)~~
-- ~~SELECT ticker, date, open, high, low, close, volume, 'polygon'~~
-- ~~FROM polygon_api_results~~
-- ~~WHERE date >= CURRENT_DATE - INTERVAL '90 days';~~
```

**Updated Approach**: *Market data will be fetched daily for current pricing only. Portfolio snapshots generated daily going forward from upload date.*

## 5. API Data Models

### 5.1 TypeScript/JavaScript Models
```typescript
// Enums matching database constraints
export enum PositionType {
  LONG = 'LONG',
  SHORT = 'SHORT',
  LC = 'LC', // Long Call
  LP = 'LP', // Long Put  
  SC = 'SC', // Short Call
  SP = 'SP'  // Short Put
}

export enum TagType {
  REGULAR = 'regular',
  STRATEGY = 'strategy'
}

// Core data interfaces matching database schema
export interface Position {
  id: string;
  portfolio_id: string;
  ticker: string;
  position_type: PositionType;
  quantity: number;
  entry_price: number;
  entry_date: Date;
  exit_price?: number;
  exit_date?: Date;
  is_active: boolean;
  
  // Options fields
  strike_price?: number;
  expiration_date?: Date;
  underlying_ticker?: string;
  
  // Calculated fields (not stored)
  current_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  
  // Relations
  tags?: Tag[];
  greeks?: PositionGreeks;
}

export interface PortfolioSnapshot {
  id: string;
  portfolio_id: string;
  snapshot_date: Date;
  frequency: 'daily' | 'weekly' | 'monthly';
  
  // Exposures
  total_value: number;
  long_exposure: number;
  short_exposure: number;
  gross_exposure: number;
  net_exposure: number;
  
  // P&L
  daily_pnl?: number;
  total_pnl?: number;
  
  // Risk Metrics
  portfolio_beta?: number;
  annualized_volatility?: number;
  position_correlation?: number;
  max_drawdown?: number;
  sharpe_ratio?: number;
  diversification_score?: number;
}
```

## 6. Database Connection Patterns

### 6.1 Connection Pool Example
```typescript
// Example using a connection pool
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20, // Maximum number of clients in the pool
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Transaction example for position creation
export async function createPosition(positionData: Partial<Position>) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    
    // Insert position
    const positionResult = await client.query(
      `INSERT INTO positions (portfolio_id, ticker, position_type, quantity, entry_price, entry_date)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING id`,
      [positionData.portfolio_id, positionData.ticker, /* ... */]
    );
    
    // Update portfolio snapshot
    await client.query(
      `UPDATE portfolio_snapshots 
       SET updated_at = NOW() 
       WHERE portfolio_id = $1 AND snapshot_date = CURRENT_DATE`,
      [positionData.portfolio_id]
    );
    
    await client.query('COMMIT');
    return positionResult.rows[0];
  } catch (e) {
    await client.query('ROLLBACK');
    throw e;
  } finally {
    client.release();
  }
}
```

## 7. Batch Processing Implementation

### 7.1 Daily Batch Process
```typescript
// Example batch job for daily calculations
export async function runDailyBatchProcess() {
  const steps = [
    { name: 'Fetch Market Data', fn: fetchMarketData },
    { name: 'Update Short Metrics', fn: updateShortSellingMetrics },
    { name: 'Calculate Returns', fn: calculatePositionReturns },
    { name: 'Update Factor Covariance', fn: updateFactorCovariance },
    { name: 'Calculate Greeks', fn: calculatePositionGreeks },
    { name: 'Calculate Correlations', fn: calculatePositionCorrelations },
    { name: 'Update Portfolio Metrics', fn: updatePortfolioMetrics },
    { name: 'Run Stress Tests', fn: runStressTests },
    { name: 'Generate Snapshots', fn: generatePortfolioSnapshots }
  ];
  
  for (const step of steps) {
    try {
      console.log(`Starting: ${step.name}`);
      await logCalculationStart(step.name);
      await step.fn();
      await logCalculationComplete(step.name);
    } catch (error) {
      await logCalculationError(step.name, error);
      throw error;
    }
  }
}
```

## 8. Common Query Patterns

### 8.1 Active Positions Query
```sql
-- Get active positions with current values
CREATE OR REPLACE FUNCTION get_active_positions(p_portfolio_id UUID)
RETURNS TABLE (
  position_id UUID,
  ticker VARCHAR,
  position_type VARCHAR,
  quantity DECIMAL,
  entry_price DECIMAL,
  current_price DECIMAL,
  market_value DECIMAL,
  unrealized_pnl DECIMAL,
  greeks JSONB
) AS $
BEGIN
  RETURN QUERY
  SELECT 
    p.id,
    p.ticker,
    p.position_type,
    p.quantity,
    p.entry_price,
    COALESCE(rq.last_price, md.close) as current_price,
    p.quantity * COALESCE(rq.last_price, md.close) as market_value,
    p.quantity * (COALESCE(rq.last_price, md.close) - p.entry_price) as unrealized_pnl,
    jsonb_build_object(
      'delta', pg.delta,
      'gamma', pg.gamma,
      'theta', pg.theta,
      'vega', pg.vega
    ) as greeks
  FROM positions p
  LEFT JOIN realtime_quotes_cache rq ON p.ticker = rq.ticker
  LEFT JOIN LATERAL (
    SELECT close FROM market_data_cache 
    WHERE ticker = p.ticker 
    ORDER BY date DESC LIMIT 1
  ) md ON true
  LEFT JOIN LATERAL (
    SELECT * FROM position_greeks
    WHERE position_id = p.id
    ORDER BY calculation_date DESC LIMIT 1
  ) pg ON true
  WHERE p.portfolio_id = p_portfolio_id 
    AND p.is_active = true;
END;
$ LANGUAGE plpgsql;
```

## 9. Complex Calculations

### 9.1 Factor Risk Contributions
```sql
-- Calculate factor contributions to portfolio risk
WITH factor_exposures AS (
  SELECT factor_id, exposure_value
  FROM portfolio_factor_exposures
  WHERE portfolio_id = $1 AND calculation_date = $2
),
covariance_data AS (
  SELECT f1.factor_id as factor1, f2.factor_id as factor2, 
         fcm.covariance
  FROM factor_exposures f1
  CROSS JOIN factor_exposures f2
  JOIN factor_covariance_matrix fcm 
    ON (fcm.factor1_id = LEAST(f1.factor_id, f2.factor_id) 
    AND fcm.factor2_id = GREATEST(f1.factor_id, f2.factor_id))
  WHERE fcm.calculation_date = $2
)
SELECT 
  fe.factor_id,
  fe.exposure_value,
  SUM(fe.exposure_value * f2.exposure_value * cd.covariance) as risk_contribution
FROM factor_exposures fe
JOIN factor_exposures f2 ON true
JOIN covariance_data cd 
  ON cd.factor1 = fe.factor_id AND cd.factor2 = f2.factor_id
GROUP BY fe.factor_id, fe.exposure_value;
```

### Diversification Score
```sql
-- Calculate portfolio diversification score (0-1, higher is more diversified)
WITH position_weights AS (
  SELECT 
    p.id,
    p.ticker,
    ABS(p.quantity * COALESCE(rq.last_price, md.close)) as position_value,
    ABS(p.quantity * COALESCE(rq.last_price, md.close)) / 
      SUM(ABS(p.quantity * COALESCE(rq.last_price, md.close))) OVER () as weight
  FROM positions p
  LEFT JOIN realtime_quotes_cache rq ON p.ticker = rq.ticker
  LEFT JOIN market_data_cache md ON p.ticker = md.ticker 
    AND md.date = (SELECT MAX(date) FROM market_data_cache WHERE ticker = p.ticker)
  WHERE p.portfolio_id = $1 AND p.is_active = true
),
weighted_correlation AS (
  SELECT 
    pw1.weight * pw2.weight * pcm.correlation as weighted_corr
  FROM position_weights pw1
  JOIN position_weights pw2 ON pw1.id < pw2.id
  JOIN position_correlation_matrix pcm 
    ON pcm.position1_id = pw1.id 
    AND pcm.position2_id = pw2.id
    AND pcm.calculation_date = CURRENT_DATE
)
SELECT 
  1 - (2 * SUM(weighted_corr) / (COUNT(DISTINCT pw.id) - 1)) as diversification_score
FROM position_weights pw, weighted_correlation;
```

### Correlated Stress Testing
```sql
-- Apply correlated stress scenario
WITH base_shocks AS (
  SELECT factor_id, shock_amount
  FROM stress_scenario_shocks
  WHERE scenario_id = $1
),
propagated_shocks AS (
  SELECT 
    f.id as factor_id,
    COALESCE(bs.shock_amount, 0) + 
    SUM(bs2.shock_amount * fcm.correlation) as total_shock
  FROM factor_definitions f
  LEFT JOIN base_shocks bs ON f.id = bs.factor_id
  LEFT JOIN base_shocks bs2 ON bs2.factor_id != f.id
  LEFT JOIN factor_covariance_matrix fcm 
    ON ((fcm.factor1_id = f.id AND fcm.factor2_id = bs2.factor_id) OR
        (fcm.factor2_id = f.id AND fcm.factor1_id = bs2.factor_id))
  WHERE fcm.calculation_date = CURRENT_DATE
  GROUP BY f.id, bs.shock_amount
)
SELECT * FROM propagated_shocks;
```

### Short Squeeze Risk Monitoring
```sql
-- Identify positions with high short squeeze risk
SELECT 
  p.id,
  p.ticker,
  p.quantity,
  ssm.cost_to_borrow_rate,
  ssm.short_interest_ratio,
  ssm.days_to_cover,
  CASE 
    WHEN ssm.cost_to_borrow_rate > 10 OR ssm.days_to_cover > 5 THEN 'HIGH'
    WHEN ssm.cost_to_borrow_rate > 5 OR ssm.days_to_cover > 3 THEN 'MEDIUM'
    ELSE 'LOW'
  END as squeeze_risk_level
FROM positions p
JOIN short_selling_metrics ssm ON p.ticker = ssm.ticker
WHERE p.position_type = 'SHORT' 
  AND p.is_active = true
  AND ssm.metric_date = CURRENT_DATE
ORDER BY ssm.cost_to_borrow_rate DESC, ssm.days_to_cover DESC;
```

## 10. Quick Reference for Developers

### 10.1 Critical Tables for MVP
- positions - Core position tracking
- portfolio_snapshots - Daily metrics and exposures
- position_greeks - Options risk metrics
- portfolio_factor_exposures - Factor analysis
- market_data_cache - Price history
- realtime_quotes_cache - Live prices

### 10.2 Key Relationships
- users 1:N portfolios
- portfolios 1:N positions
- positions N:M tags (through position_tags)
- positions 1:N position_greeks
- positions 1:N position_factor_betas
- portfolios 1:N portfolio_snapshots
- portfolios 1:N portfolio_factor_exposures

### 10.3 Common Development Tasks

#### 10.3.1 Adding a New Position
1. Insert into positions table
2. Add any tags via position_tags
3. Trigger recalculation of portfolio metrics
4. Update realtime_quotes_cache if needed

#### 10.3.2 Running Daily Batch
1. Check calculation_audit_log for last run
2. Execute batch process steps in order
3. Verify all calculations completed
4. Check for any anomalies in metrics

#### 10.3.3 Implementing What-If Analysis
1. Create modeling_session
2. Clone current positions to session
3. Apply modifications
4. Calculate pro-forma metrics
5. Compare with baseline

### 10.4 Performance Tips

#### 10.4.1 Database Level
- Recent market data (90 days)
- Current factor covariance matrix
- Active position factor betas

#### 10.4.2 Application Level
- Real-time factor exposures
- Stress test results (5 minute TTL)
- Contribution analysis (until position change)

#### 10.4.3 Pre-Calculation
- All display metrics computed nightly
- Stress scenarios run proactively
- Attribution pre-aggregated by common groupings

### 10.5 Common Pitfalls to Avoid
- N+1 Queries: Use joins or batch fetching
- Missing Indexes: Check query plans
- Stale Caches: Implement proper invalidation
- Transaction Scope: Keep transactions small
- Time Zone Issues: Always use UTC internally