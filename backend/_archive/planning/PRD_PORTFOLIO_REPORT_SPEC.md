# Portfolio Report Generator PRD
**Product Requirements Document - LLM-Optimized Portfolio Analytics Report**

> ⚠️ **IMPLEMENTATION STATUS (2025-08-26 15:20 PST)**: Report generation has been fully implemented in Phase 2. See [TODO2.md](../../TODO2.md) Section 2.3 for completion details. Reports are generated successfully for all 3 demo portfolios with graceful degradation for missing data.

## 1. Overview

### 1.1 Purpose
Generate comprehensive portfolio analytics reports in human and machine-readable formats for consumption by Large Language Models (LLMs) like ChatGPT. Reports will enable LLMs to provide intelligent portfolio recommendations and answer analytical questions for users.

### 1.2 Primary Audience
- **Primary**: LLMs (ChatGPT, Claude, etc.) for portfolio analysis and recommendations
- **Secondary**: Human analysts and portfolio managers for direct reading

### 1.3 Scope
Generate detailed reports for each of the 3 demo portfolios with complete calculation engine output including:
- Portfolio summary metrics and exposures
- Risk analytics and factor exposures  
- Position-level details with Greeks
- Correlation matrices and stress test results
- Market data and performance metrics

---

## 2. Report Structure

### 2.1 Output Format - Hybrid File Approach
Generate 3 complementary files per portfolio:

1. **Human-Readable Report**: `{portfolio_name}_report_{YYYY-MM-DD}.md`
   - Executive summary and key insights
   - Narrative analysis and recommendations
   - High-level metrics and alerts
   - Optimized for human consumption

2. **Detailed Data Export**: `{portfolio_name}_data_{YYYY-MM-DD}.json`
   - Complete structured data from all 8 batch engines
   - Factor exposures, correlations, stress tests
   - Historical time series
   - Optimized for LLM deep analysis

3. **Position Details**: `{portfolio_name}_positions_{YYYY-MM-DD}.csv`
   - Complete position holdings with all fields
   - Greeks, exposures, P&L by position
   - Tags and strategy classifications
   - Optimized for spreadsheet analysis and LLM position-level queries

**Update Frequency**: Daily (post-batch processing completion)

### 2.2 Report Sections

#### 2.2.1 Executive Summary
- Portfolio metadata (name, owner, total value)
- Performance metrics (P&L, returns, best/worst performers)
- Risk metrics (beta, volatility, correlation, drawdown)

#### 2.2.2 Portfolio Overview  
- Exposure summary table (Long/Short/Gross/Net)
- Asset allocation breakdown (stocks vs options)
- Top holdings by exposure
- Position counts by type

#### 2.2.3 Risk Analytics
- Complete factor exposures table (all 7 factors with percentiles)
- Complete stress test results table (all scenarios)
- Greeks summary for options positions
- Correlation metrics

#### 2.2.4 Historical Performance
- Recent performance data from portfolio snapshots
- Daily P&L history (last 30 days)
- Performance vs calculation date range

---

## 3. Data Requirements

### 3.1 Core Data Sources
Must integrate outputs from all 8 batch calculation engines:

1. **Market Data Sync** - Current prices for all positions
2. **Portfolio Aggregation** - Exposure calculations, P&L
3. **Greeks Calculation** - Options risk metrics
4. **Factor Analysis** - 7-factor model exposures
5. **Market Risk Scenarios** - Treasury yield impact analysis
6. **Stress Testing** - Comprehensive stress test scenarios
7. **Position Correlations** - Pairwise correlation matrix
8. **Portfolio Snapshot** - Historical performance tracking

### 3.2 Demo Portfolio Coverage

#### 3.2.1 Balanced Individual Investor Portfolio
- **User**: demo_individual@sigmasight.com
- **Total Value**: $485,000
- **Focus**: Diversified long-only with mutual funds and ETFs
- **Key Features**: Tech growth tilt, dividend income, core holdings

#### 3.2.2 Sophisticated High Net Worth Portfolio  
- **User**: demo_hnw@sigmasight.com
- **Total Value**: $2,850,000
- **Focus**: Blue chip concentration with alternative assets
- **Key Features**: Large positions, gold/commodities hedge

#### 3.2.3 Long/Short Equity Hedge Fund Style Portfolio
- **User**: demo_hedgefundstyle@sigmasight.com  
- **Total Value**: $3,200,000
- **Focus**: Market-neutral with options overlay
- **Key Features**: Short positions, complex options strategies

---

## 4. Report Content Specifications

### 4.1 Human-Readable Report (.md file)

#### 4.1.1 Executive Summary Format
```markdown
# Portfolio Analytics Report
**{Portfolio Name}** | {Owner} | Generated: {Timestamp}

## Executive Summary

**Total Value**: ${total_value:,.2f} ({daily_change:+.2f}% today)

### Performance Metrics
- Daily P&L: ${daily_pnl:,.2f} ({daily_pnl_pct:+.2f}%)
- Portfolio Value: ${total_value:,.2f}
- Total Positions: {position_count}
- Last Updated: {last_calculation_date}

### Risk Metrics  
- Portfolio Beta: {portfolio_beta:.3f} vs SPY
- Average Correlation: {avg_correlation:.3f}
- Gross Exposure: ${gross_exposure:,.2f}
- Net Exposure: ${net_exposure:,.2f}
```

#### 4.1.2 Portfolio Snapshot
```markdown
## Portfolio Snapshot

### Allocation Overview
- **{stock_count} Stock Positions**: ${stock_exposure:,.0f} ({stock_pct:.0f}%)
- **{option_count} Options Positions**: ${option_exposure:,.0f} ({option_pct:.0f}%)  
- **Net Directional Exposure**: ${net_exposure:,.0f} ({net_bias})

### Top Holdings (by Exposure)
1. {top1_symbol}: ${top1_exposure:,.0f} ({top1_type})
2. {top2_symbol}: ${top2_exposure:,.0f} ({top2_type})
3. {top3_symbol}: ${top3_exposure:,.0f} ({top3_type})

### Strategy Highlights
{strategy_summary}
```

#### 4.1.3 Risk & Factor Analysis
```markdown
## Risk Analytics

### Factor Exposures
| Factor | Exposure | Percentile |
|--------|----------|------------|
| Market Beta | {market_beta:+.3f} | {market_beta_percentile}th |
| Momentum | {momentum:+.3f} | {momentum_percentile}th |
| Value | {value:+.3f} | {value_percentile}th |
| Growth | {growth:+.3f} | {growth_percentile}th |
| Quality | {quality:+.3f} | {quality_percentile}th |
| Size | {size:+.3f} | {size_percentile}th |
| Short Interest | {short_interest:+.3f} | {short_interest_percentile}th |
| Volatility | {volatility_factor:+.3f} | {volatility_percentile}th |

### Stress Test Results

| Scenario | Impact ($) | Impact (%) |
|----------|------------|------------|
| Market Up 10% | ${market_up_dollar:+,.0f} | {market_up_impact:+.1f}% |
| Market Down 10% | ${market_down_dollar:+,.0f} | {market_down_impact:+.1f}% |
| Rates Up 0.25% | ${rates_up_dollar:+,.0f} | {rates_up_impact:+.1f}% |
| Rates Down 0.25% | ${rates_down_dollar:+,.0f} | {rates_down_impact:+.1f}% |
| Oil Up 5% | ${oil_up_dollar:+,.0f} | {oil_up_impact:+.1f}% |
| Oil Down 5% | ${oil_down_dollar:+,.0f} | {oil_down_impact:+.1f}% |
| DAX Up 10% | ${dax_up_dollar:+,.0f} | {dax_up_impact:+.1f}% |
| DAX Down 10% | ${dax_down_dollar:+,.0f} | {dax_down_impact:+.1f}% |

### Greeks Summary (Options Positions)
| Greek | Total | Average per Position |
|-------|-------|---------------------|
| Delta | {total_delta:.2f} | {avg_delta:.3f} |
| Gamma | {total_gamma:.2f} | {avg_gamma:.3f} |
| Theta | {total_theta:.2f} | {avg_theta:.3f} |
| Vega | {total_vega:.2f} | {avg_vega:.3f} |
| Rho | {total_rho:.2f} | {avg_rho:.3f} |
```

### 4.2 Detailed Data Export (.json file)
**Complete structured data for LLM deep analysis**

#### 4.2.1 JSON Structure Overview
```json
{
  "portfolio": {
    "metadata": {
      "name": "Portfolio Name",
      "owner": "user@example.com", 
      "generated_at": "2024-08-07T10:30:00Z",
      "total_value": 3200000.00,
      "calculation_date": "2024-08-07"
    },
    "performance": {
      "daily_pnl": 15600.00,
      "daily_return": 0.0049,
      "monthly_return": 0.0234,
      "ytd_return": 0.1456
    },
    "exposures": {
      "long_exposure": 4200000.00,
      "short_exposure": -1400000.00,
      "gross_exposure": 5600000.00,
      "net_exposure": 2800000.00
    },
    "risk_metrics": {
      "portfolio_beta": 1.15,
      "annualized_volatility": 0.185,
      "max_drawdown": -0.087,
      "average_correlation": 0.589
    },
    "factor_exposures": {
      "market_beta": {"value": 1.15, "percentile": 78},
      "momentum": {"value": 0.45, "percentile": 65},
      "value": {"value": -0.22, "percentile": 25},
      "growth": {"value": 0.67, "percentile": 85},
      "quality": {"value": 0.31, "percentile": 60},
      "size": {"value": -0.18, "percentile": 35},
      "short_interest": {"value": 0.12, "percentile": 55},
      "volatility": {"value": -0.08, "percentile": 40}
    },
    "stress_tests": [
      {
        "scenario": "Market Down 10%",
        "impact_dollar": -312675.25,
        "impact_percent": -9.77,
        "risk_level": "high"
      }
    ],
    "correlations": {
      "symbols": ["AAPL", "MSFT", "GOOGL"],
      "matrix": [[1.0, 0.742, 0.856], [0.742, 1.0, 0.789], [0.856, 0.789, 1.0]]
    },
    "historical_snapshots": [
      {"date": "2024-08-01", "value": 3150000.00, "daily_return": 0.0023},
      {"date": "2024-08-02", "value": 3168000.00, "daily_return": 0.0057}
    ]
  }
}
```

### 4.3 Position Details Export (.csv file) 
**Complete position data for spreadsheet analysis**

#### 4.3.1 CSV Column Structure
```csv
Symbol,Position_Type,Quantity,Entry_Price,Current_Price,Market_Value,Cost_Basis,Unrealized_PnL,Realized_PnL,Delta,Gamma,Theta,Vega,Rho,Delta_Dollars,Gamma_Dollars,Tags,Strategy_Tags,Underlying_Symbol,Strike_Price,Expiry_Date,Days_To_Expiry,Implied_Volatility,Entry_Date,Sector,Industry
AAPL,LONG,1500,225.00,235.50,353250.00,337500.00,15750.00,0.00,1.0,0.0,0.0,0.0,0.0,353250.00,0.00,"Long Momentum","",AAPL,,,,,2024-01-08,Technology,Consumer Electronics
MSFT250919P00380000,SP,-80,5.00,3.25,26000.00,40000.00,14000.00,0.00,-0.65,0.02,0.08,-0.12,-0.05,-20800.00,640.00,"Options Overlay","",MSFT,380.00,2025-09-19,408,0.22,2024-01-20,Technology,Software
```

### 4.4 File Organization
```
reports/
└── portfolio_12345/
    └── 2024-08-07/
        ├── balanced_individual_report_2024-08-07.md      # Human-readable
        ├── balanced_individual_data_2024-08-07.json      # LLM analysis  
        └── balanced_individual_positions_2024-08-07.csv   # Position details
```

**Benefits of Hybrid Approach:**
- ✅ **Human Report**: Clean, narrative-focused, easy to read
- ✅ **JSON Data**: Complete structured data for LLM deep dive analysis  
- ✅ **CSV Positions**: All position details for spreadsheet work
- ✅ **Focused Files**: Each file optimized for its specific use case
- ✅ **No Clutter**: Human report stays clean without large data tables

---

## 5. LLM Optimization Features

### 5.1 Structured Data Blocks
- **Clear JSON/CSV demarcation** for easy parsing
- **Consistent field naming** across all data structures
- **Metadata inclusion** (dates, methodology, data sources)
- **Units and precision** clearly specified

### 5.2 Context Enrichment
- **Benchmark comparisons** for all metrics
- **Percentile rankings** for factor exposures
- **Risk level classifications** (low/medium/high)
- **Trend indicators** for time series data

### 5.3 Analysis Guidance
- **Key insights** highlighted in executive summary
- **Attention flags** for unusual metrics or positions
- **Recommendation frameworks** for common scenarios
- **Risk warnings** for concentration or exposure issues

---

## 6. Technical Implementation

### 6.1 Simplified Report Generator Structure
```
app/reports/
├── __init__.py
├── portfolio_report_generator.py    # Main generation logic for all 3 files
└── __main__.py                      # CLI entry point for manual generation
```

**Rationale**: Simple single-file approach with direct string formatting, no separate templates needed for 3-5 day timeline.

### 6.2 Simplified Implementation Approach
```python
def generate_portfolio_reports(portfolio_id: str) -> dict:
    """Generate all 3 portfolio report files using direct database queries"""
    # 1. Query data using existing calculation outputs
    portfolio_data = query_portfolio_snapshot(portfolio_id)
    positions_data = query_positions_with_greeks(portfolio_id) 
    factor_data = query_factor_exposures(portfolio_id)
    stress_data = query_stress_test_results(portfolio_id)
    correlation_data = query_correlation_data(portfolio_id)
    
    # 2. Generate reports with direct string formatting
    markdown_report = f"""# {portfolio_data.name} Analytics Report
## Executive Summary
**Total Value**: ${portfolio_data.total_value:,.2f}
**Daily P&L**: ${portfolio_data.daily_pnl:,.2f}
..."""
    
    # 3. Generate JSON using model serialization
    json_export = {
        "portfolio": portfolio_data.dict(),
        "factor_exposures": [f.dict() for f in factor_data],
        "stress_tests": [s.dict() for s in stress_data],
        ...
    }
    
    # 4. Generate CSV using pandas DataFrame
    csv_data = build_positions_dataframe(positions_data)
    
    return save_reports(portfolio_id, markdown_report, json_export, csv_data)
```

### 6.3 Integration Points
- **Database**: Query existing tables (no new schemas needed)
- **Batch Orchestrator**: Add as final step after all calculations
- **CLI**: Simple command for manual generation
- **File System**: Save to `reports/{portfolio_id}/` directory

---

## 7. Implementation Todo List
**Realistic Timeline: 3-5 Days**

### 7.1 Day 1: Data Mapping & Core Infrastructure
- [ ] Map all PRD placeholders to actual database fields and calculation outputs
- [ ] Verify demo portfolios have complete calculation engine data (all 8 engines)
- [ ] Create `app/reports/` directory and `portfolio_report_generator.py` 
- [ ] Implement data collection functions using existing database queries
- [ ] Define output file structure: `reports/{portfolio_id}/{date}/`

### 7.2 Day 2: Report Generation Implementation
- [ ] Implement markdown report generation with direct string formatting (no templates)
- [ ] Build executive summary using PortfolioSnapshot + CorrelationCalculation data
- [ ] Build portfolio snapshot using calculate_portfolio_exposures() output
- [ ] Build factor analysis table using PositionFactorExposure data
- [ ] Build stress test table using StressTestResult data
- [ ] Build Greeks summary using aggregate_portfolio_greeks() output

### 7.3 Day 3: JSON & CSV Export Implementation
- [ ] Implement JSON export using direct database model serialization
- [ ] Include all 8 calculation engine outputs in structured JSON format
- [ ] Implement CSV export with complete position details and calculated fields
- [ ] Add Greeks, factor exposures, and metadata columns to CSV
- [ ] Validate all data fields populate correctly (no missing/null critical data)

### 7.4 Day 4: Demo Portfolio Testing & Integration
- [ ] Generate all 3 files for Balanced Individual Investor Portfolio
- [ ] Generate all 3 files for Sophisticated High Net Worth Portfolio  
- [ ] Generate all 3 files for Long/Short Hedge Fund Style Portfolio
- [ ] Add report generation as final step in batch_orchestrator_v2.py
- [ ] Test end-to-end: batch processing → report generation
- [ ] Validate human reports are clean and readable

### 7.5 Day 5: CLI Interface & Final Polish
- [ ] Create CLI command: `python -m app.reports {portfolio_id}`
- [ ] Add error handling for missing data with graceful degradation
- [ ] Test LLM consumption of JSON/CSV files (manual ChatGPT upload test)
- [ ] Add basic logging and status reporting
- [ ] Final validation: all demo portfolios generate complete reports

---

## 8. Success Criteria

### 8.1 Functional Requirements
- ✅ Generate complete reports for all 3 demo portfolios
- ✅ Include data from all 8 batch calculation engines  
- ✅ Produce human-readable markdown format
- ✅ Include LLM-optimized JSON and CSV data blocks
- ✅ Update automatically after daily batch processing

### 8.2 Quality Requirements
- ✅ All numerical data accurate to source systems
- ✅ Consistent formatting and structure across portfolios
- ✅ Complete error handling with graceful degradation
- ✅ Performance: Generate reports in < 30 seconds
- ✅ LLM parsing: Successfully consumed by ChatGPT/Claude

### 8.3 Integration Requirements
- ✅ Seamless integration with existing batch processing
- ✅ Compatible with current database schema
- ✅ Minimal impact on system performance
- ✅ Configurable for future portfolio types
- ✅ Extensible for additional data sources

---

## 9. Future Enhancements

### 9.1 Advanced Analytics
- Scenario analysis with custom stress tests
- Monte Carlo simulation results
- Options flow analysis and Greeks scenarios
- Sector and style attribution analysis

### 9.2 Interactive Features  
- Web-based report viewer
- Real-time report updates
- Custom report filtering and views
- Export to multiple formats (PDF, Excel)

### 9.3 AI Enhancement
- Natural language insights generation
- Automated recommendation engine
- Anomaly detection and alerting
- Predictive analytics integration

---

**Document Version**: 1.0  
**Last Updated**: August 7, 2024  
**Next Review**: August 14, 2024