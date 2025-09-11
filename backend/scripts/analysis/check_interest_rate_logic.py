"""
Check the interest rate calculation logic in stress tests
"""
import asyncio
from app.calculations.stress_testing import STRESS_SCENARIOS, FACTOR_MAPPING

def analyze_interest_rate_logic():
    """
    Check how interest rates are defined in stress scenarios
    """
    print("=" * 80)
    print("INTEREST RATE STRESS TEST CONFIGURATION ANALYSIS")
    print("=" * 80)
    
    # 1. Check all stress scenarios
    print("\n1. ALL DEFINED STRESS SCENARIOS:")
    print("-" * 40)
    for i, scenario in enumerate(STRESS_SCENARIOS, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Type: {scenario.get('type', 'unknown')}")
        if 'shocks' in scenario:
            for shock in scenario['shocks']:
                factor = shock.get('factor', 'Unknown')
                magnitude = shock.get('magnitude', 0)
                print(f"   - {factor}: {magnitude:+.1%} shock")
    
    # 2. Find interest rate specific scenarios
    print("\n" + "=" * 80)
    print("2. INTEREST RATE SPECIFIC SCENARIOS:")
    print("-" * 40)
    
    interest_scenarios = []
    for scenario in STRESS_SCENARIOS:
        # Check if scenario involves interest rates
        has_interest = False
        
        # Check scenario name
        if 'interest' in scenario['name'].lower() or 'rate' in scenario['name'].lower():
            has_interest = True
        
        # Check shocks
        if 'shocks' in scenario:
            for shock in scenario['shocks']:
                if 'Interest' in shock.get('factor', ''):
                    has_interest = True
        
        if has_interest:
            interest_scenarios.append(scenario)
    
    if interest_scenarios:
        for scenario in interest_scenarios:
            print(f"\n📊 {scenario['name']}")
            print(f"   Description: {scenario.get('description', 'N/A')}")
            
            if 'shocks' in scenario:
                for shock in scenario['shocks']:
                    if 'Interest' in shock.get('factor', ''):
                        magnitude = shock.get('magnitude', 0)
                        magnitude_pct = magnitude * 100
                        
                        print(f"\n   Interest Rate Shock: {magnitude:+.4f} ({magnitude_pct:+.2f}%)")
                        
                        # Analyze if this is reasonable
                        if abs(magnitude) >= 0.10:  # 10% or more
                            print(f"   ⚠️ ISSUE FOUND: Magnitude of {abs(magnitude_pct):.1f}% is excessive!")
                            print(f"      - Expected: 0.25% to 3% (25-300 basis points)")
                            print(f"      - Actual: {abs(magnitude_pct):.1f}%")
                            print(f"      - This is {abs(magnitude)/0.01:.0f}x larger than a typical 1% shock")
                            print(f"      - LIKELY CAUSE: Using 0.10 to mean 10bp instead of 10%")
                        elif abs(magnitude) >= 0.05:  # 5% or more
                            print(f"   ⚠️ WARNING: {abs(magnitude_pct):.1f}% shock is quite large")
                            print(f"      - Typical range: 0.25% to 3%")
                        else:
                            print(f"   ✅ Magnitude seems reasonable for stress test")
    else:
        print("\n❌ No interest rate scenarios found!")
    
    # 3. Check factor mapping
    print("\n" + "=" * 80)
    print("3. FACTOR MAPPING FOR INTEREST RATES:")
    print("-" * 40)
    
    interest_mappings = {}
    for key, value in FACTOR_MAPPING.items():
        if 'interest' in key.lower() or 'rate' in key.lower():
            interest_mappings[key] = value
        elif 'interest' in value.lower() or 'rate' in value.lower():
            interest_mappings[key] = value
    
    if interest_mappings:
        print("\nFound interest rate mappings:")
        for stressed_factor, exposure_factor in interest_mappings.items():
            print(f"  {stressed_factor} → {exposure_factor}")
    else:
        print("\n❌ No interest rate factor mapping found!")
        print("This explains why we see: 'No exposure found for Interest_Rate'")
    
    # 4. Check if Interest_Rate is in the factor mapping
    print("\n" + "=" * 80)
    print("4. CHECKING FOR 'Interest_Rate' IN MAPPINGS:")
    print("-" * 40)
    
    if 'Interest_Rate' in FACTOR_MAPPING:
        print(f"✅ 'Interest_Rate' maps to: {FACTOR_MAPPING['Interest_Rate']}")
    else:
        print("❌ 'Interest_Rate' not found in FACTOR_MAPPING")
        print("   Available keys:", list(FACTOR_MAPPING.keys()))
        
        # Check if it's supposed to map to something
        print("\n   Checking what factors we DO have exposures for...")
        from app.calculations.factors import FACTOR_ETFS
        print("   Factor ETFs defined:", list(FACTOR_ETFS.keys()))
    
    # 5. Summary and recommendations
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS:")
    print("=" * 80)
    
    has_excessive_shocks = any(
        abs(shock.get('magnitude', 0)) >= 0.10 
        for scenario in interest_scenarios 
        for shock in scenario.get('shocks', [])
        if 'Interest' in shock.get('factor', '')
    )
    
    if has_excessive_shocks:
        print("\n🔴 CRITICAL ISSUE: Interest rate shocks are 10-100x too large")
        print("   - Some scenarios have 10%+ interest rate shocks")
        print("   - Normal range should be 0.25% to 3%")
        print("   - This will cause unrealistic stress test results")
        print("\n   RECOMMENDED FIX:")
        print("   - Divide interest rate shock magnitudes by 10")
        print("   - Example: Change 0.10 to 0.01 (10% → 1%)")
    
    if not interest_mappings:
        print("\n🟡 MAPPING ISSUE: Interest rate factor not properly mapped")
        print("   - Stress tests can't find interest rate exposures")
        print("   - Need to add 'Interest_Rate' to FACTOR_MAPPING")
        print("\n   RECOMMENDED FIX:")
        print("   - Add to FACTOR_MAPPING: 'Interest_Rate': 'Interest Rate Beta'")
    
    if not has_excessive_shocks and interest_mappings:
        print("\n✅ Interest rate configuration appears correct")

if __name__ == "__main__":
    analyze_interest_rate_logic()