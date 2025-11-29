#!/usr/bin/env python3
"""
Comprehensive Storage Calculator for SigmaSight Database
Estimates storage requirements for 750 symbols over 180 days across all models
"""

def calculate_comprehensive_storage():
    """Calculate total storage requirements for SigmaSight system"""
    
    # Configuration
    SYMBOLS = 750
    DAYS = 180
    PORTFOLIOS = 3  # Current demo setup
    POSITIONS_PER_PORTFOLIO = 21  # Average from demo data
    TOTAL_POSITIONS = PORTFOLIOS * POSITIONS_PER_PORTFOLIO
    
    print(f"Storage Calculation for SigmaSight System")
    print(f"Configuration: {SYMBOLS} symbols, {DAYS} days, {PORTFOLIOS} portfolios")
    print(f"Total Positions: {TOTAL_POSITIONS}")
    print("=" * 70)
    
    storage_breakdown = {}
    
    # 1. Core User/Portfolio Data
    users_bytes = 3 * 200  # 3 users, ~200 bytes each
    portfolios_bytes = 3 * 300  # 3 portfolios, ~300 bytes each
    positions_bytes = TOTAL_POSITIONS * 400  # ~400 bytes per position
    tags_bytes = 20 * 100  # Assume 20 tags, ~100 bytes each
    core_data_mb = (users_bytes + portfolios_bytes + positions_bytes + tags_bytes) / (1024 * 1024)
    storage_breakdown["Core Data (Users/Portfolios/Positions)"] = core_data_mb
    
    # 2. Market Data Cache (daily price data for positions)
    # This is the primary market data storage
    market_cache_bytes = TOTAL_POSITIONS * DAYS * 150  # 150 bytes per position per day
    market_cache_mb = market_cache_bytes / (1024 * 1024)
    storage_breakdown["Market Data Cache (daily prices)"] = market_cache_mb
    
    # 3. Position Greeks (calculated daily for options)
    # Assume 30% of positions are options with Greeks
    options_positions = int(TOTAL_POSITIONS * 0.3)
    greeks_bytes = options_positions * DAYS * 200  # 200 bytes per Greeks calculation
    greeks_mb = greeks_bytes / (1024 * 1024)
    storage_breakdown["Position Greeks (options)"] = greeks_mb
    
    # 4. Factor Definitions and Exposures
    factor_definitions = 15 * 200  # 15 factors, ~200 bytes each
    # Factor exposures calculated daily for each position
    factor_exposures_bytes = TOTAL_POSITIONS * DAYS * 15 * 16  # 15 factors, 16 bytes per exposure
    factor_exposures_mb = (factor_definitions + factor_exposures_bytes) / (1024 * 1024)
    storage_breakdown["Factor Exposures (daily calculations)"] = factor_exposures_mb
    
    # 5. Portfolio Snapshots (daily portfolio state)
    snapshot_bytes = PORTFOLIOS * DAYS * 1000  # 1KB per portfolio per day
    snapshot_mb = snapshot_bytes / (1024 * 1024)
    storage_breakdown["Portfolio Snapshots (daily)"] = snapshot_mb
    
    # 6. Correlation Analysis
    # Pairwise correlations between positions (calculated periodically)
    correlation_pairs = (TOTAL_POSITIONS * (TOTAL_POSITIONS - 1)) // 2
    correlation_bytes = correlation_pairs * 50  # 50 bytes per correlation pair
    correlation_clusters = 10 * 200  # 10 clusters, 200 bytes each
    correlations_mb = (correlation_bytes + correlation_clusters) / (1024 * 1024)
    storage_breakdown["Correlation Analysis"] = correlations_mb
    
    # 7. Risk Metrics and Scenarios
    risk_scenarios = 20 * 300  # 20 scenarios, 300 bytes each
    stress_scenarios = 10 * 400  # 10 stress scenarios, 400 bytes each
    stress_results_bytes = PORTFOLIOS * 10 * DAYS * 200  # Results for each portfolio/scenario/day
    risk_mb = (risk_scenarios + stress_scenarios + stress_results_bytes) / (1024 * 1024)
    storage_breakdown["Risk Metrics & Stress Testing"] = risk_mb
    
    # 8. Interest Rate Beta (for fixed income positions)
    # Assume 20% of positions are fixed income
    fixed_income_positions = int(TOTAL_POSITIONS * 0.2)
    ir_beta_bytes = fixed_income_positions * DAYS * 100  # 100 bytes per IR beta calculation
    ir_beta_mb = ir_beta_bytes / (1024 * 1024)
    storage_breakdown["Interest Rate Beta"] = ir_beta_mb
    
    # 9. Fund Holdings (for ETF/mutual fund positions)
    # Assume 25% of positions are funds with holdings data
    fund_positions = int(TOTAL_POSITIONS * 0.25)
    fund_holdings_bytes = fund_positions * 50 * 200  # 50 holdings per fund, 200 bytes each
    fund_holdings_mb = fund_holdings_bytes / (1024 * 1024)
    storage_breakdown["Fund Holdings"] = fund_holdings_mb
    
    # 10. Batch Job Tracking
    batch_jobs = DAYS * 8  # 8 calculation engines run daily
    batch_schedules = 20  # 20 different job schedules
    batch_bytes = (batch_jobs * 300) + (batch_schedules * 200)
    batch_mb = batch_bytes / (1024 * 1024)
    storage_breakdown["Batch Job Tracking"] = batch_mb
    
    # 11. Export History and Modeling Sessions
    exports = 100 * 300  # 100 export records, 300 bytes each
    modeling_sessions = 50 * 500  # 50 modeling sessions, 500 bytes each
    misc_mb = (exports + modeling_sessions) / (1024 * 1024)
    storage_breakdown["Export/Modeling History"] = misc_mb
    
    # Calculate totals
    total_raw_mb = sum(storage_breakdown.values())
    
    # Add database overhead (indexes, WAL, metadata, fragmentation)
    overhead_multiplier = 2.5  # Conservative estimate for PostgreSQL
    total_with_overhead_mb = total_raw_mb * overhead_multiplier
    total_with_overhead_gb = total_with_overhead_mb / 1024
    
    # Display breakdown
    print("\nStorage Breakdown (Raw Data):")
    for category, mb in storage_breakdown.items():
        print(f"  {category:<45} {mb:>8.2f} MB")
    
    print(f"\n{'='*70}")
    print(f"Raw Data Total:                               {total_raw_mb:>8.2f} MB")
    print(f"With Database Overhead (2.5x):                {total_with_overhead_mb:>8.2f} MB")
    print(f"Total Storage Requirement:                    {total_with_overhead_gb:>8.3f} GB")
    
    # Railway plan analysis
    print(f"\n🚀 Railway Plan Analysis:")
    if total_with_overhead_gb <= 0.5:
        spare = 0.5 - total_with_overhead_gb
        print(f"  ✅ Free/Trial (0.5GB):     Sufficient with {spare:.3f} GB spare ({spare/0.5*100:.1f}% headroom)")
    elif total_with_overhead_gb <= 5:
        spare = 5 - total_with_overhead_gb
        print(f"  ✅ Hobby (5GB):           Sufficient with {spare:.2f} GB spare ({spare/5*100:.1f}% headroom)")
    elif total_with_overhead_gb <= 50:
        spare = 50 - total_with_overhead_gb
        print(f"  ✅ Pro/Team (50GB):       Sufficient with {spare:.1f} GB spare ({spare/50*100:.1f}% headroom)")
    else:
        print(f"  ❌ Exceeds Pro/Team limits ({total_with_overhead_gb:.2f} GB > 50GB)")
    
    # Cost analysis
    monthly_cost = total_with_overhead_gb * 0.15  # $0.15 per GB per month
    print(f"\n💰 Railway Storage Cost: ${monthly_cost:.3f}/month")
    
    # Growth projections
    print(f"\n📈 Growth Projections:")
    for multiplier, scenario in [(2, "2x growth"), (5, "5x growth"), (10, "10x growth")]:
        scaled_gb = total_with_overhead_gb * multiplier
        scaled_cost = scaled_gb * 0.15
        if scaled_gb <= 0.5:
            plan = "Free/Trial"
        elif scaled_gb <= 5:
            plan = "Hobby"
        elif scaled_gb <= 50:
            plan = "Pro/Team"
        else:
            plan = "Exceeds Pro/Team"
        print(f"  {scenario:<12} {scaled_gb:>6.2f} GB  {plan:<15} ${scaled_cost:>6.2f}/month")
    
    return total_with_overhead_gb, storage_breakdown

if __name__ == "__main__":
    calculate_comprehensive_storage()