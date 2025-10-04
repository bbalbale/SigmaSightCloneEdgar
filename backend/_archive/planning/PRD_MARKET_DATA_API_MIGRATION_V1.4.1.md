# MARKET DATA API MIGRATION PLAN

## Goal
Choose a cost-effective solution that adds mutual fund holdings data while keeping the existing system mostly intact.

## Sequential Testing Plan (4-5 days)

This plan tests both scenarios in sequence to generate a comprehensive comparison report.

### Test Portfolio
```python
# ALL tickers from Ben's Mock Portfolios - comprehensive test
TEST_ITEMS = {
    # Portfolio 1: Balanced Individual Investor
    "portfolio_1_stocks": [
        "AAPL", "MSFT", "AMZN", "GOOGL", "TSLA", 
        "NVDA", "JNJ", "JPM", "V"
    ],
    "portfolio_1_mutual_funds": [
        "FXNAX",  # Fidelity US Large Cap Growth
        "FCNTX",  # Fidelity Contrafund
        "FMAGX",  # Fidelity Magellan
        "VTIAX",  # Vanguard Total International
    ],
    "portfolio_1_etfs": ["VTI", "BND", "VNQ"],
    
    # Portfolio 2: Sophisticated High Net Worth
    "portfolio_2_stocks": [
        "SPY", "QQQ", "AAPL", "MSFT", "AMZN", 
        "GOOGL", "BRK.B", "JPM", "JNJ", "NVDA", 
        "META", "UNH", "V", "HD", "PG"
    ],
    "portfolio_2_etfs": ["GLD", "DJP"],  # Alternative investments
    
    # Portfolio 3: Long/Short Equity Hedge Fund Style
    "portfolio_3_longs": [
        "NVDA", "MSFT", "AAPL", "GOOGL", "META", 
        "AMZN", "TSLA", "AMD", "BRK.B", "JPM", 
        "JNJ", "UNH", "V"
    ],
    "portfolio_3_shorts": [
        "NFLX", "SHOP", "ZOOM", "PELOTON", "ROKU",
        "XOM", "F", "GE", "C"
    ],
    "portfolio_3_options": [
        # Long Options
        "SPY 2025-09-19 460C",
        "QQQ 2025-08-15 420C", 
        "VIX 2025-07-16 25C",
        "NVDA 2025-10-17 800C",
        # Short Options
        "AAPL 2025-08-15 200P",
        "MSFT 2025-09-19 380P",
        "TSLA 2025-08-15 300C",
        "META 2025-09-19 450P"
    ]
}

# Consolidated unique list for testing
ALL_STOCKS = list(set(
    TEST_ITEMS["portfolio_1_stocks"] + 
    TEST_ITEMS["portfolio_2_stocks"] + 
    TEST_ITEMS["portfolio_3_longs"] + 
    TEST_ITEMS["portfolio_3_shorts"]
))

ALL_MUTUAL_FUNDS = TEST_ITEMS["portfolio_1_mutual_funds"]

ALL_ETFS = list(set(
    TEST_ITEMS["portfolio_1_etfs"] + 
    TEST_ITEMS["portfolio_2_etfs"]
))

ALL_OPTIONS = TEST_ITEMS["portfolio_3_options"]
```

### Two Data Provider Scenarios to Test

Based on cost analysis and feature requirements, we'll test these two scenarios:

#### Scenario 1: TradeFeeds + Polygon
- **TradeFeeds Professional Plan**: $149/month
  - 22,000 API calls/month 
  - 30 calls/minute rate limit
  - ETF/Mutual Fund holdings: 20X multiplier (each call = 20 credits)
  - Stocks: 1X multiplier
- **Polygon Options Starter**: $29/month
  - Unlimited options API calls
- **Total Cost**: $178/month

**Option A**: Use TradeFeeds for both Stocks + ETF/Mutual Fund holdings
**Option B**: Use TradeFeeds for ETF/Mutual Fund holdings only + Polygon Stocks Starter ($29/month) = $207/month total

#### Scenario 2: Financial Modeling Prep + Polygon  
- **FMP Ultimate Plan**: $139/month
  - 3,000 API calls/minute
  - Includes Stocks, ETF/Mutual Fund holdings
- **Polygon Options Starter**: $29/month
  - Unlimited options API calls  
- **Total Cost**: $168/month

### Cost Analysis for 20 Users

**API Usage Estimates (per month):**
- Per user: ~756 API calls (26 stocks × 22 days + 8 ETF/MF holdings + 8 options × 22 days)
- 20 users total: ~15,120 API calls/month
- ETF/Mutual Fund calls: 160 calls/month (8 funds × 20 users)

#### Scenario 1 Cost Breakdown:
**Option A - TradeFeeds for All Data:**
- Stock calls: 11,440 (15,120 - 3,520 options - 160 ETF/MF) = 11,440 credits
- ETF/MF calls: 160 × 20 multiplier = 3,200 credits  
- **Total TradeFeeds usage**: 14,640 credits (within 22,000 limit ✓)
- **Monthly cost**: $178

**Option B - TradeFeeds ETF/MF + Polygon Stocks:**
- TradeFeeds: 160 calls × 20 = 3,200 credits (within limit ✓)
- Polygon Stocks: 11,440 calls (unlimited ✓)
- **Monthly cost**: $207

#### Scenario 2 Cost Breakdown:
- FMP: 11,600 calls for stocks + ETF/MF holdings (within rate limits ✓)
- Polygon: 3,520 options calls (unlimited ✓)  
- **Monthly cost**: $168

**Recommendation**: Scenario 2 (FMP + Polygon) offers best value at $168/month with room to scale.

### Testing Timeline

**Day 1-2: Scenario 1 Testing (TradeFeeds + Polygon)**
- Set up TradeFeeds API access
- Test TradeFeeds for stocks and ETF/MF holdings
- Test Polygon for options chains
- Generate Scenario 1 results

**Day 3-4: Scenario 2 Testing (FMP + Polygon)**
- Set up FMP API access  
- Test FMP for stocks and ETF/MF holdings
- Test Polygon for options chains
- Generate Scenario 2 results

**Day 5: Comparison & Decision**
- Generate comprehensive comparison report
- Analyze cost vs. data quality trade-offs
- Make final recommendation

### Test Scripts
Create directory: `scripts/test_api_providers/`

#### 1. Main Test Script: `test_new_apis.py`
```python
import asyncio
import json
import csv
from datetime import datetime
from decimal import Decimal
import pandas as pd

async def test_scenario(scenario_name, providers_config, output_dir="./api_test_results"):
    """Test a complete data provider scenario"""
    
    print(f"\n{'='*60}")
    print(f"Testing {scenario_name}")
    print(f"Providers: {', '.join(providers_config.keys())}")
    print(f"{'='*60}")
    
    results = {
        "scenario": scenario_name,
        "providers": providers_config,
        "test_date": datetime.now().isoformat(),
        "stocks": {},
        "mutual_funds": {},
        "etfs": {},
        "options": {},
        "costs": {},
        "summary": {}
    }
    
    # Test 1: Stock Prices 
    stock_provider = providers_config.get("stocks")
    print(f"\n1. Testing Stock Prices via {stock_provider}...")
    print(f"   Testing {len(ALL_STOCKS)} unique stocks from all portfolios")
    
    stocks_to_test = ALL_STOCKS[:5]  # Test first 5 for detail
    for symbol in stocks_to_test:
        try:
            prices = await fetch_stock_prices(stock_provider, symbol)
            print(f"  ✓ {symbol}: {len(prices)} days of history")
            results["stocks"][symbol] = {"success": True, "days": len(prices), "provider": stock_provider}
        except Exception as e:
            print(f"  ✗ {symbol}: {str(e)}")
            results["stocks"][symbol] = {"success": False, "error": str(e), "provider": stock_provider}
    
    # Quick test remaining stocks
    remaining_stocks = ALL_STOCKS[5:]
    success_count = 0
    for symbol in remaining_stocks:
        try:
            prices = await fetch_stock_prices(stock_provider, symbol)
            success_count += 1
            results["stocks"][symbol] = {"success": True, "days": len(prices), "provider": stock_provider}
        except:
            results["stocks"][symbol] = {"success": False, "provider": stock_provider}
    
    print(f"  → Tested {len(ALL_STOCKS)} total stocks: {success_count + len(stocks_to_test)} successful")
    
    # Test 2: Mutual Fund Holdings (CRITICAL - export all)
    funds_provider = providers_config.get("funds") 
    print(f"\n2. Testing Mutual Fund Holdings via {funds_provider}...")
    for symbol in ALL_MUTUAL_FUNDS:
        try:
            holdings = await fetch_fund_holdings(funds_provider, symbol)
            print(f"  ✓ {symbol}: {len(holdings)} holdings found")
            
            # Export to CSV for manual review
            export_holdings_to_csv(symbol, holdings, funds_provider, output_dir)
            
            # Analyze holdings quality
            total_weight = sum(h.get('weight', 0) for h in holdings)
            has_names = all(h.get('name') for h in holdings[:10])
            
            results["mutual_funds"][symbol] = {
                "success": True,
                "count": len(holdings),
                "total_weight": total_weight,
                "has_security_names": has_names,
                "sample": holdings[:3] if holdings else [],
                "provider": funds_provider
            }
        except Exception as e:
            print(f"  ✗ {symbol}: {str(e)}")
            results["mutual_funds"][symbol] = {"success": False, "error": str(e), "provider": funds_provider}
    
    # Test 2b: ETF Holdings (also important)
    print(f"\n2b. Testing ETF Holdings via {funds_provider}...")
    for symbol in ALL_ETFS:
        try:
            holdings = await fetch_fund_holdings(funds_provider, symbol)
            print(f"  ✓ {symbol}: {len(holdings)} holdings found")
            export_holdings_to_csv(symbol, holdings, funds_provider, output_dir)
            results["etfs"][symbol] = {"success": True, "count": len(holdings), "provider": funds_provider}
        except Exception as e:
            print(f"  ✗ {symbol}: {str(e)}")
            results["etfs"][symbol] = {"success": False, "error": str(e), "provider": funds_provider}
    
    # Test 3: Options Chains (test sample from Portfolio 3)
    options_provider = providers_config.get("options")
    print(f"\n3. Testing Options Chains via {options_provider}...")
    for option_str in ALL_OPTIONS[:4]:  # Test first 4 in detail
        parts = option_str.split()
        symbol = parts[0]
        expiry = parts[1]
        strike_type = parts[2]  # e.g., "460C" or "200P"
        
        try:
            chain = await fetch_options_chain(options_provider, symbol, expiry)
            print(f"  ✓ {symbol} {expiry}: {len(chain)} contracts found")
            
            # Check data quality
            has_greeks = any(c.get('delta') for c in chain[:10])
            has_iv = any(c.get('implied_volatility') for c in chain[:10])
            
            results["options"][f"{symbol}_{expiry}"] = {
                "success": True,
                "contracts": len(chain),
                "has_greeks": has_greeks,
                "has_iv": has_iv,
                "specific_strike": strike_type,
                "provider": options_provider
            }
        except Exception as e:
            print(f"  ✗ {symbol}: {str(e)}")
            results["options"][f"{symbol}_{expiry}"] = {"success": False, "error": str(e), "provider": options_provider}
    
    # Calculate costs based on actual usage
    print(f"\n4. Calculating Costs for {scenario_name}...")
    results["costs"] = calculate_scenario_costs(scenario_name, providers_config, results)
    
    # Save full results
    with open(f"{output_dir}/{scenario_name.replace(' ', '_')}_test_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to {output_dir}/{scenario_name.replace(' ', '_')}_test_results.json")
    return results

def calculate_scenario_costs(scenario_name, providers_config, test_results):
    """Calculate monthly costs based on actual API usage"""
    costs = {}
    
    if "Scenario 1" in scenario_name:  # TradeFeeds + Polygon
        # TradeFeeds costs
        stock_calls = len([r for r in test_results["stocks"].values() if r.get("success")])
        mf_calls = len([r for r in test_results["mutual_funds"].values() if r.get("success")]) 
        etf_calls = len([r for r in test_results["etfs"].values() if r.get("success")])
        
        # Apply 20X multiplier for ETF/MF calls
        tradefeeds_credits = stock_calls + (mf_calls + etf_calls) * 20
        costs["TradeFeeds"] = {
            "base_cost": 149,
            "credits_used": tradefeeds_credits,
            "credits_limit": 22000,
            "within_limit": tradefeeds_credits <= 22000
        }
        
        # Polygon costs
        options_calls = len([r for r in test_results["options"].values() if r.get("success")])
        costs["Polygon"] = {
            "options_cost": 29,
            "stock_cost": 29 if providers_config.get("stocks") == "Polygon" else 0,
            "calls_used": options_calls
        }
        
        costs["total_monthly"] = 149 + 29 + (29 if providers_config.get("stocks") == "Polygon" else 0)
        
    elif "Scenario 2" in scenario_name:  # FMP + Polygon
        costs["FMP"] = {
            "base_cost": 99,
            "calls_per_minute_limit": 3000,
            "unlimited_calls": True
        }
        
        options_calls = len([r for r in test_results["options"].values() if r.get("success")])
        costs["Polygon"] = {
            "options_cost": 29,
            "calls_used": options_calls
        }
        
        costs["total_monthly"] = 99 + 29
    
    return costs

def export_holdings_to_csv(fund_symbol, holdings, provider_name, output_dir):
    """Export holdings to CSV for manual inspection"""
    filename = f"{output_dir}/{provider_name}_{fund_symbol}_holdings.csv"
    
    with open(filename, 'w', newline='') as f:
        if holdings:
            writer = csv.DictWriter(f, fieldnames=holdings[0].keys())
            writer.writeheader()
            writer.writerows(holdings)
    
    print(f"    → Exported to {filename}")

# Run sequential scenario tests
async def main():
    import os
    os.makedirs("./api_test_results", exist_ok=True)
    
    results = []
    
    # Scenario 1: TradeFeeds + Polygon  
    print("\n" + "="*80)
    print("STARTING SCENARIO 1 TESTING (TradeFeeds + Polygon)")
    print("="*80)
    
    scenario_1a_config = {
        "stocks": "TradeFeeds",
        "funds": "TradeFeeds", 
        "options": "Polygon"
    }
    scenario_1a = await test_scenario("Scenario 1A: TradeFeeds All + Polygon Options", scenario_1a_config)
    results.append(scenario_1a)
    
    scenario_1b_config = {
        "stocks": "Polygon",
        "funds": "TradeFeeds",
        "options": "Polygon" 
    }
    scenario_1b = await test_scenario("Scenario 1B: TradeFeeds Funds + Polygon Stocks/Options", scenario_1b_config)
    results.append(scenario_1b)
    
    # Scenario 2: FMP + Polygon
    print("\n" + "="*80)
    print("STARTING SCENARIO 2 TESTING (FMP + Polygon)")
    print("="*80)
    
    scenario_2_config = {
        "stocks": "FMP",
        "funds": "FMP",
        "options": "Polygon"
    }
    scenario_2 = await test_scenario("Scenario 2: FMP All + Polygon Options", scenario_2_config)
    results.append(scenario_2)
    
    # Generate comprehensive comparison report
    print("\n" + "="*80)
    print("GENERATING FINAL COMPARISON REPORT")
    print("="*80)
    generate_scenario_comparison_report(results)
```

#### 2. Comparison Report Generator: `generate_report.py`
```python
def generate_scenario_comparison_report(results):
    """Create a comprehensive comparison of both scenarios"""
    
    report = []
    report.append("# Data Provider Scenarios Comparison Report")
    report.append(f"\nGenerated: {datetime.now()}")
    report.append("\nThis report compares TradeFeeds+Polygon vs FMP+Polygon scenarios for SigmaSight.")
    
    # Executive Summary
    report.append("\n## Executive Summary")
    
    scenario_summaries = []
    for r in results:
        scenario_name = r['scenario']
        total_cost = r['costs']['total_monthly']
        scenario_summaries.append(f"- **{scenario_name}**: ${total_cost}/month")
    
    report.extend(scenario_summaries)
    
    # Cost Analysis
    report.append("\n## Cost Analysis (Monthly)")
    report.append("| Scenario | Base Costs | Total Monthly | Scalability | Notes |")
    report.append("|----------|------------|---------------|-------------|-------|")
    
    for r in results:
        scenario = r['scenario']
        costs = r['costs']
        total = costs['total_monthly']
        
        # Determine scalability
        if 'TradeFeeds' in costs:
            credits_used = costs['TradeFeeds']['credits_used']
            credits_limit = costs['TradeFeeds']['credits_limit']
            scalability = f"{credits_used}/{credits_limit} credits" if credits_used <= credits_limit else "❌ Exceeds limit"
        else:
            scalability = "✅ Unlimited"
        
        # Build cost breakdown
        cost_details = []
        for provider, details in costs.items():
            if provider != 'total_monthly' and isinstance(details, dict):
                if 'base_cost' in details:
                    cost_details.append(f"{provider}: ${details['base_cost']}")
                elif 'options_cost' in details:
                    cost_details.append(f"{provider}: ${details['options_cost']}")
        
        cost_str = " + ".join(cost_details)
        notes = "ETF/MF 20X multiplier" if "TradeFeeds" in scenario else "Unlimited calls"
        
        report.append(f"| {scenario} | {cost_str} | ${total} | {scalability} | {notes} |")
    
    # Data Quality Analysis
    report.append("\n## Mutual Fund Holdings Data Quality")
    report.append("| Scenario | FXNAX | FCNTX | FMAGX | VTIAX | Avg Holdings | Provider |")
    report.append("|----------|-------|-------|-------|-------|--------------|----------|")
    
    for r in results:
        scenario = r['scenario']
        mf_data = r['mutual_funds']
        
        counts = []
        provider = ""
        
        row = f"| {scenario} "
        for symbol in ['FXNAX', 'FCNTX', 'FMAGX', 'VTIAX']:
            if symbol in mf_data and mf_data[symbol].get('success'):
                count = mf_data[symbol]['count']
                counts.append(count)
                provider = mf_data[symbol].get('provider', '')
                row += f"| {count} "
            else:
                row += "| ❌ "
        
        avg = sum(counts) / len(counts) if counts else 0
        row += f"| {avg:.0f} | {provider} |"
        report.append(row)
    
    # Options Data Quality
    report.append("\n## Options Chain Data Quality")  
    report.append("| Scenario | Sample Contracts | Greeks Available | IV Available | Provider |")
    report.append("|----------|------------------|------------------|--------------|----------|")
    
    for r in results:
        scenario = r['scenario']
        options_data = r['options']
        
        total_contracts = sum(opt.get('contracts', 0) for opt in options_data.values() if opt.get('success'))
        has_greeks = any(opt.get('has_greeks') for opt in options_data.values() if opt.get('success'))
        has_iv = any(opt.get('has_iv') for opt in options_data.values() if opt.get('success'))
        provider = next((opt.get('provider') for opt in options_data.values() if opt.get('success')), '')
        
        greeks_str = "✅ Yes" if has_greeks else "❌ No"
        iv_str = "✅ Yes" if has_iv else "❌ No"
        
        report.append(f"| {scenario} | {total_contracts} | {greeks_str} | {iv_str} | {provider} |")
    
    # Recommendations
    report.append("\n## Recommendations")
    
    # Find best cost scenario
    best_cost_scenario = min(results, key=lambda x: x['costs']['total_monthly'])
    best_cost = best_cost_scenario['costs']['total_monthly']
    
    report.append(f"\n### Cost Winner: {best_cost_scenario['scenario']}")
    report.append(f"**Monthly Cost**: ${best_cost}")
    
    # Check if all data requirements are met
    report.append(f"\n### Data Quality Assessment:")
    for r in results:
        scenario_name = r['scenario']
        
        # Check mutual funds success rate
        mf_success = sum(1 for mf in r['mutual_funds'].values() if mf.get('success'))
        mf_total = len(r['mutual_funds'])
        
        # Check options success rate  
        opt_success = sum(1 for opt in r['options'].values() if opt.get('success'))
        opt_total = len(r['options'])
        
        report.append(f"\n**{scenario_name}:**")
        report.append(f"- Mutual Funds: {mf_success}/{mf_total} successful")
        report.append(f"- Options: {opt_success}/{opt_total} successful")
        
        if mf_success == mf_total and opt_success == opt_total:
            report.append(f"- ✅ **Meets all requirements**")
        else:
            report.append(f"- ❌ **Missing data coverage**")
    
    # Final recommendation
    report.append(f"\n### Final Recommendation")
    report.append(f"Based on cost analysis and data coverage, **{best_cost_scenario['scenario']}** is recommended.")
    report.append(f"This provides the best balance of cost (${best_cost}/month) and comprehensive data coverage.")
    
    # Save report
    with open("./api_test_results/SCENARIO_COMPARISON_REPORT.md", 'w') as f:
        f.write('\n'.join(report))
    
    print("\n✅ Scenario comparison report saved to ./api_test_results/SCENARIO_COMPARISON_REPORT.md")
    
    # Also create a simple decision summary
    with open("./api_test_results/DECISION_SUMMARY.md", 'w') as f:
        f.write(f"# Decision Summary\\n\\n")
        f.write(f"**Recommended Solution**: {best_cost_scenario['scenario']}\\n")
        f.write(f"**Monthly Cost**: ${best_cost}\\n")
        f.write(f"**Decision Date**: {datetime.now().strftime('%Y-%m-%d')}\\n\\n")
        f.write(f"**Rationale**: Provides complete data coverage at the lowest monthly cost.\\n")
    
    print("✅ Decision summary saved to ./api_test_results/DECISION_SUMMARY.md")
```

### Decision Criteria
1. **Mutual Fund Holdings Quality** (40% - Critical)
   - Coverage: Do all 4 test funds have holdings data?
   - Completeness: 40+ holdings per fund expected
   - Data fields: Symbol, name, weight/percentage, shares
   - Total weights: Should sum to ~90-100%

2. **Stock Price Data** (20% - Must Have)
   - Historical data: 1+ years available
   - All test symbols supported
   - Accurate OHLCV data

3. **Options Chain Data** (20% - Must Have)  
   - Full chain with multiple expiries
   - Greeks available (delta, gamma, theta, vega)
   - Implied volatility data

4. **Cost & Simplicity** (20%)
   - Under $200/month
   - Simple API to integrate
   - Good documentation

### Expected Output Files
After running sequential scenario tests, you'll have:
```
api_test_results/
├── Scenario_1A:_TradeFeeds_All_+_Polygon_Options_test_results.json
├── Scenario_1B:_TradeFeeds_Funds_+_Polygon_Stocks/Options_test_results.json
├── Scenario_2:_FMP_All_+_Polygon_Options_test_results.json
├── TradeFeeds_FXNAX_holdings.csv    # Holdings data from each provider
├── TradeFeeds_FCNTX_holdings.csv
├── TradeFeeds_FMAGX_holdings.csv 
├── TradeFeeds_VTIAX_holdings.csv
├── FMP_FXNAX_holdings.csv
├── FMP_FCNTX_holdings.csv
├── FMP_FMAGX_holdings.csv
├── FMP_VTIAX_holdings.csv
├── SCENARIO_COMPARISON_REPORT.md     # Comprehensive comparison
└── DECISION_SUMMARY.md              # Final recommendation
```

### What to Look for in Holdings CSVs
1. **Number of holdings**: Should see 50-200+ per fund
2. **Data completeness**: 
   - Security identifiers (ticker/CUSIP)
   - Security names (not just tickers)
   - Weights/percentages
   - Share counts (nice to have)
3. **Weight totals**: Should sum to 90-100%
4. **Recognizable names**: Top holdings should match fund's strategy

## Detailed Implementation Plan (5 days)

### Day-by-Day Testing Schedule

#### Day 1: Setup & Scenario 1A Testing
**Morning:**
- [ ] Sign up for TradeFeeds Professional Plan ($149/mo trial)
- [ ] Get TradeFeeds API key and review documentation
- [ ] Create `scripts/test_api_providers/` directory
- [ ] Set up test environment and dependencies

**Afternoon:**
- [ ] Run Scenario 1A: TradeFeeds for Stocks/Funds + Polygon for Options
- [ ] Test all 4 mutual funds holdings (FXNAX, FCNTX, FMAGX, VTIAX) 
- [ ] Export holdings to CSV for manual inspection
- [ ] Test stock prices for top 26 symbols
- [ ] Generate Scenario 1A results JSON

#### Day 2: Scenario 1B & TradeFeeds Analysis
**Morning:**
- [ ] Run Scenario 1B: TradeFeeds for Funds only + Polygon for Stocks/Options
- [ ] Compare TradeFeeds credit usage between 1A vs 1B
- [ ] Verify ETF/MF 20X multiplier impact on costs

**Afternoon:**
- [ ] Analyze all TradeFeeds CSV holdings exports
- [ ] Check data quality: security names, weights, completeness
- [ ] Test options chains via Polygon (same for both scenarios)
- [ ] Generate Scenario 1B results JSON

#### Day 3: FMP Setup & Scenario 2 Testing  
**Morning:**
- [ ] Sign up for Financial Modeling Prep Ultimate Plan ($99/mo trial)
- [ ] Get FMP API key and review documentation
- [ ] Review FMP holdings endpoint and rate limits

**Afternoon:**
- [ ] Run Scenario 2: FMP for Stocks/Funds + Polygon for Options
- [ ] Test all mutual funds holdings via FMP
- [ ] Export FMP holdings to CSV
- [ ] Test stock prices via FMP
- [ ] Generate Scenario 2 results JSON

#### Day 4: Data Quality Analysis
**Morning:**
- [ ] Compare mutual fund holdings quality:
  - TradeFeeds vs FMP holdings count per fund
  - Data completeness (names, weights, symbols)
  - Total weight percentages
  - Recognizable top holdings

**Afternoon:**
- [ ] Verify options data consistency (Polygon used in all scenarios)
- [ ] Test API rate limits practically for each provider
- [ ] Document any data gaps or quality issues
- [ ] Prepare cost calculations based on actual usage

#### Day 5: Final Comparison & Decision
**Morning:**
- [ ] Run comprehensive comparison report generation
- [ ] Generate `SCENARIO_COMPARISON_REPORT.md`
- [ ] Generate `DECISION_SUMMARY.md` 
- [ ] Review all CSV exports manually

**Afternoon:**
- [ ] Final recommendation based on:
  - Cost analysis (including scalability for 20 users)
  - Data coverage completeness
  - Data quality assessment
  - Implementation complexity
- [ ] Document next steps for implementation

### Implementation After Decision

#### If Choosing TradeFeeds + Polygon Scenario:

Modify the existing `MarketDataService`:

```python
# app/services/market_data_service.py

class MarketDataService:
    def __init__(self):
        self.polygon_client = RESTClient(POLYGON_API_KEY)
        self.tradefeeds_client = TradeFeedsClient(TRADEFEEDS_API_KEY)  # NEW
    
    async def fetch_stock_prices(self, symbols):
        # CHANGE: Route based on chosen scenario 
        if USE_TRADEFEEDS_FOR_STOCKS:
            return await self.tradefeeds_client.get_stock_prices(symbols)
        else:
            return await self.polygon_client.get_stock_prices(symbols)
    
    async def fetch_mutual_fund_holdings(self, symbol):
        # NEW: Add this method - always use TradeFeeds in this scenario
        return await self.tradefeeds_client.get_fund_holdings(symbol)
    
    async def fetch_options_chain(self, symbol):
        # NO CHANGE: Keep using Polygon
        return await self.polygon_client.get_options(symbol)
```

#### If Choosing FMP + Polygon Scenario:

Replace with FMP client:

```python
# app/services/market_data_service.py

class MarketDataService:
    def __init__(self):
        self.polygon_client = RESTClient(POLYGON_API_KEY)
        self.fmp_client = FMPClient(FMP_API_KEY)  # NEW
    
    async def fetch_stock_prices(self, symbols):
        # CHANGE: Route to FMP for stocks
        return await self.fmp_client.get_stock_prices(symbols)
    
    async def fetch_mutual_fund_holdings(self, symbol):
        # NEW: Add this method using FMP
        return await self.fmp_client.get_fund_holdings(symbol)
    
    async def fetch_options_chain(self, symbol):
        # NO CHANGE: Keep using Polygon
        return await self.polygon_client.get_options(symbol)
```

## Minimal TODO List

### Week 1: Test & Decide
- [ ] Day 1: Get trial API keys
- [ ] Day 2: Run test script, check mutual fund holdings quality
- [ ] Day 3: Pick winner, document decision

### Week 2: Implement
- [ ] Day 1: Add new API client to requirements.txt
- [ ] Day 2: Update MarketDataService (add new client, modify 1-3 methods)
- [ ] Day 3: Test with real portfolio data
- [ ] Day 4: Update .env.example and deployment configs
- [ ] Day 5: Deploy and monitor

### That's It!

## Future-Proofing (Do Later)

When you have 100+ users and need more flexibility:
1. Add a simple provider config in .env:
   ```
   STOCK_DATA_PROVIDER=eodhd
   OPTIONS_DATA_PROVIDER=polygon
   ```

2. Add a factory pattern:
   ```python
   def get_stock_data_client():
       if settings.STOCK_DATA_PROVIDER == "eodhd":
           return EODHDClient()
       elif settings.STOCK_DATA_PROVIDER == "polygon":
           return PolygonClient()
   ```

But don't build this now - you don't need it yet.

## Migration Checklist

- [ ] Test new API with actual mutual fund tickers
- [ ] Update MarketDataService (change ~50 lines of code)
- [ ] Add new API key to environment variables
- [ ] Test all existing features still work
- [ ] Update any batch jobs that call the service
- [ ] Deploy

## What We're NOT Doing (Yet)
- Complex routing engines
- Multiple fallback providers  
- Sophisticated caching layers
- Provider health monitoring
- Cost tracking systems

These can all wait until you have real users and real problems to solve.

## Implementation Questions for AI Coding Agent

### 1. Provider-Specific API Details
- What are the actual API endpoints for each provider (EODHD, FMP, TwelveData) for:
  - Fetching mutual fund holdings
  - Getting stock prices
  - Retrieving options chains
- What authentication method does each use (API key in header vs query parameter)?

### 2. Response Format Normalization
- Each provider likely returns data in different formats. Should the test script include normalization logic to convert all responses to a common format? For example:
```python
# EODHD might return: {"symbol": "AAPL", "weight": 5.2}
# FMP might return: {"ticker": "AAPL", "percentage": 5.2}
# Should we normalize to: {"symbol": "AAPL", "weight": 5.2, "name": "Apple Inc."}
```

### 3. Missing Implementation Functions
- The test script references `fetch_stock_prices()`, `fetch_fund_holdings()`, and `fetch_options_chain()` but doesn't show their implementations
- Should these be provider-specific adapters?

### 4. Rate Limiting
- Should the test script include rate limiting logic to avoid hitting API limits during testing?
- What are the rate limits for each provider's trial/free tier?

### 5. Error Handling Specifics
- What specific errors should we catch and how should we handle them?
- Examples: symbol not found, API limit exceeded, network timeout

### 6. Data Quality Metrics
- For the "Data Quality" assessment in the comparison report, what specific criteria determine "Good" vs "Limited"?
- Is it just the presence of security names, or should we check for other fields?

### 7. Options Contract Format
- The test portfolio shows options as strings like "SPY 2025-09-19 460C"
- Do the APIs expect this format, or do they need separate parameters (underlying, expiry, strike, type)?

### 8. Provider Adapter Pattern
- Should we create a common interface like this?
```python
class MarketDataProvider(ABC):
    @abstractmethod
    async def get_stock_price(self, symbol: str) -> Optional[StockPrice]:
        pass
    
    @abstractmethod
    async def get_mutual_fund_holdings(self, symbol: str) -> Optional[List[Holding]]:
        pass
    
    @abstractmethod
    async def get_options_chain(self, underlying: str, expiry: date) -> Optional[List[OptionContract]]:
        pass

# Then implement:
# EODHDProvider(MarketDataProvider)
# FMPProvider(MarketDataProvider)
# TwelveDataProvider(MarketDataProvider)
```

### 9. Test Execution Strategy
- Should we run tests against all providers in parallel or sequentially?
- How do we handle API keys for testing (environment variables)?
- Should failed API calls be retried during testing?

### 10. Holdings Update Frequency
- How often do mutual fund holdings typically update (quarterly?)?
- Should we cache holdings data differently than price data?
- What's the staleness tolerance for holdings data in production?

### 11. Development Testing Approach
- Should we create mock responses for each provider first?
- Example mock data structure for consistent testing?
- How to verify data quality without manual inspection of 192 test cases?