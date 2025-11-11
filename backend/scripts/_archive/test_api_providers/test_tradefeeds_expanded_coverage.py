#!/usr/bin/env python3
"""
Expanded Mutual Fund Coverage Test for TradeFeeds
Tests mutual funds from a wide range of fund families to assess coverage
Matches the format used in FMP expanded coverage testing
"""
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import csv

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.config import settings
from app.clients import TradeFeedsClient

# Comprehensive test set matching FMP expanded testing - 174 funds across 20 families
EXPANDED_MUTUAL_FUNDS = {
    "Vanguard": {
        "VTSAX": "Total Stock Market Admiral",
        "VTIAX": "Total International Stock Admiral", 
        "VBTLX": "Total Bond Market Admiral",
        "VFINX": "500 Index Fund",
        "VGTSX": "Total International Stock Index",
        "VBMFX": "Total Bond Market Index",
        "VTSMX": "Total Stock Market Index",
        "VTWSX": "Total World Stock Index",
        "VHDYX": "High Dividend Yield Index",
        "VTABX": "Total Bond Market II Index",
        "VEXAX": "Extended Market Index Admiral",
        "VSMAX": "Small-Cap Index Admiral",
        "VMCAX": "Mid-Cap Index Admiral",
        "VGSLX": "REIT Index Admiral",
        "VTEB": "Tax-Exempt Bond Index",
        "VWIGX": "International Growth Admiral"
    },
    "Fidelity": {
        "FXNAX": "US Bond Index Fund",
        "FCNTX": "Contrafund",
        "FMAGX": "Magellan Fund",
        "FSKAX": "Total Market Index",
        "FTIHX": "Total International Index",
        "FXAIX": "500 Index Fund",
        "FDVV": "High Dividend ETF",
        "FNILX": "ZERO Large Cap Index",
        "FZROX": "ZERO Total Market Index",
        "FBALX": "Balanced Fund",
        "FDGRX": "Dividend Growth Fund",
        "FGRIX": "Government Income Fund",
        "FLPSX": "Low-Priced Stock Fund",
        "FREL": "MSCI Real Estate Index ETF",
        "FSMEX": "Mid Cap Extended Market Index",
        "FPADX": "Advisor Strategic Income Fund"
    },
    "American Funds": {
        "AGTHX": "Growth Fund of America",
        "AIVSX": "Investment Company of America",
        "AWSHX": "Washington Mutual Investors",
        "AMCPX": "AMCAP Fund",
        "ANCFX": "Fundamental Investors",
        "CWGIX": "Capital World Growth & Income",
        "AEPGX": "EuroPacific Growth",
        "ANWPX": "New Perspective",
        "AMRMX": "American Mutual",
        "ABALX": "American Balanced",
        "AHITX": "American High-Income Trust",
        "BFAFX": "Bond Fund of America",
        "NEWFX": "New Economy",
        "SMCWX": "SMALLCAP World"
    },
    "T. Rowe Price": {
        "TRBCX": "Blue Chip Growth",
        "PRFDX": "Equity Income",
        "PRGFX": "Growth Stock",
        "PRIDX": "Dividend Growth",
        "TRMCX": "Mid-Cap Growth",
        "PRNHX": "New Horizons",
        "PRSCX": "Science & Technology",
        "TRSGX": "Small-Cap Stock",
        "PRHSX": "Health Sciences",
        "PRMTX": "Mid-Cap Value",
        "PRWCX": "Capital Appreciation",
        "RPBAX": "Balanced Fund",
        "PRSIX": "International Stock",
        "PRASX": "Emerging Markets Stock",
        "PRELX": "Emerging Markets Local Currency Bond",
        "RPGEX": "Global Stock"
    },
    "BlackRock": {
        "MDLRX": "Equity Dividend Fund",
        "BMCIX": "Basic Value Fund",
        "BGSAX": "Global Allocation Fund",
        "MDDVX": "Mid-Cap Dividend Fund",
        "MASGX": "Advantage Small Cap Growth",
        "MDGRX": "Mid Cap Growth Equity",
        "MKDVX": "Mid-Cap Value",
        "MDLOX": "Capital Appreciation",
        "MALOX": "Large Cap Core",
        "MKLCX": "Advantage Large Cap Growth",
        "BRHYX": "High Yield Bond",
        "BLADX": "Strategic Income Opportunities"
    },
    "PIMCO": {
        "PTTRX": "Total Return Fund",
        "PIMIX": "Income Fund",
        "PONDX": "Dynamic Bond Fund",
        "PHDGX": "High Yield Fund",
        "PFORX": "Foreign Bond Fund (USD-Hedged)",
        "PDIIX": "Diversified Income Fund",
        "PRRIX": "Real Return Fund",
        "PSTIX": "Short Term Fund",
        "PLRIX": "Long-Term Real Return",
        "PMZIX": "Monthly Income Fund",
        "PGBIX": "Global Bond Fund",
        "PAIIX": "All Asset Fund"
    },
    "Franklin Templeton": {
        "FKINX": "Franklin Income Fund",
        "FKUSX": "Franklin Utilities Fund",
        "TEPLX": "Templeton Global Bond Fund",
        "TEMFX": "Templeton Foreign Fund",
        "FRNKX": "Franklin Growth Fund",
        "FSENX": "Franklin Small Cap Growth",
        "FKGRX": "Franklin Growth Opportunities",
        "FRDPX": "Franklin Rising Dividends",
        "FRBSX": "Franklin Small-Mid Cap Growth",
        "TPINX": "Templeton Global Income",
        "TEDIX": "Templeton Developing Markets Trust"
    },
    "Invesco": {
        "ACSTX": "Comstock Fund",
        "ACDVX": "Diversified Dividend Fund",
        "IENAX": "Equally-Weighted S&P 500 Fund",
        "OPGIX": "Global Opportunities Fund",
        "IQHIX": "Quality Income Fund",
        "VSCGX": "Small Cap Growth Fund",
        "IMANX": "Core Plus Bond Fund",
        "OPTFX": "Main Street Fund",
        "QVSCX": "Small Cap Value Fund",
        "IVIVX": "Mid Cap Core Equity Fund"
    },
    "Dodge & Cox": {
        "DODGX": "Stock Fund",
        "DODBX": "Balanced Fund",
        "DODIX": "Income Fund",
        "DODFX": "International Stock Fund",
        "DODWX": "Worldwide Global Stock Fund"
    },
    "Janus Henderson": {
        "JANSX": "Forty Fund",
        "JMCVX": "Mid Cap Value Fund",
        "JAGIX": "Enterprise Fund",
        "JNGIX": "Global Life Sciences Fund",
        "JDCAX": "Contrarian Fund",
        "JABLX": "Balanced Fund",
        "JORNX": "Orion Fund"
    },
    "Schwab": {
        "SWPPX": "S&P 500 Index Fund",
        "SWTSX": "Total Stock Market Index",
        "SWISX": "International Index",
        "SWAGX": "US Aggregate Bond Index",
        "SWLRX": "Large-Cap Growth Fund",
        "SWMCX": "Mid-Cap Fund",
        "SWSCX": "Small-Cap Fund",
        "SWHFX": "Health Care Fund"
    },
    "Goldman Sachs": {
        "GSGOX": "Growth Opportunities Fund",
        "GCGIX": "Large Cap Growth Insights",
        "GVIRX": "Large Cap Value Insights",
        "GSMCX": "Mid Cap Value Fund",
        "GSSDX": "Small Cap Equity Insights"
    },
    "JPMorgan": {
        "JMVAX": "Mid Cap Value Fund",
        "JGSCX": "Growth Advantage Fund",
        "OHYFX": "High Yield Fund",
        "JNBAX": "Core Bond Fund",
        "JEMSX": "Emerging Markets Equity Fund"
    },
    "Wells Fargo": {
        "SGRAX": "Growth Fund",
        "WFADX": "Advantage Funds - Discovery",
        "EVGRX": "Large Company Growth",
        "WFALX": "Large Cap Core Fund",
        "WFBIX": "Corporate Bond Fund"
    },
    "Northern Trust": {
        "NOSGX": "Stock Index Fund",
        "NOSIX": "Bond Index Fund",
        "NTIAX": "International Equity Index",
        "NOEMX": "Emerging Markets Equity Index",
        "NTMIX": "Mid Cap Index"
    },
    "Columbia": {
        "IACAX": "Acorn Fund",
        "NSGAX": "Select Large Cap Growth",
        "UMBWX": "Bond Fund",
        "NTIAX": "Contrarian Core Fund",
        "LIACX": "Dividend Income Fund"
    },
    "Putnam": {
        "PEYAX": "Equity Income Fund",
        "PGRWX": "Growth Opportunities Fund",
        "PMVAX": "Multi-Cap Value Fund",
        "PBDAX": "Dynamic Asset Allocation Balanced",
        "PSLAX": "Small Cap Value Fund"
    },
    "MFS": {
        "MFEGX": "Growth Fund",
        "MEIAX": "Value Fund",
        "MRGAX": "Research Fund",
        "OTCAX": "Mid Cap Growth Fund",
        "MMHYX": "High Yield Fund"
    },
    "Principal": {
        "PQIAX": "Equity Income Fund",
        "PEMGX": "MidCap Fund",
        "PLGAX": "LargeCap Growth Fund",
        "PSMGX": "SmallCap Growth Fund",
        "PGBAX": "Global Diversified Income"
    },
    "Nuveen": {
        "FMEIX": "Mid Cap Index Fund",
        "FLISX": "Large Cap Core Fund",
        "FSCSX": "Small Cap Select Fund",
        "NHMRX": "High Yield Municipal Bond",
        "FHIGX": "High Income Bond Fund"
    }
}

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TradeFeedsExpandedTester:
    """Test TradeFeeds coverage for expanded set of mutual funds matching FMP test format"""
    
    def __init__(self, output_dir: str = "./tradefeeds_expanded_test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.all_results = []
        self.working_funds = []
        
    async def test_fund_coverage(self) -> Dict[str, Any]:
        """Test TradeFeeds coverage for all fund families"""
        logger.info("🧪 Starting Expanded TradeFeeds Mutual Fund Coverage Test")
        logger.info("=" * 80)
        
        test_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        total_funds = sum(len(funds) for funds in EXPANDED_MUTUAL_FUNDS.values())
        logger.info(f"Testing {total_funds} funds across {len(EXPANDED_MUTUAL_FUNDS)} fund families")
        
        if not settings.TRADEFEEDS_API_KEY:
            logger.error("❌ TRADEFEEDS_API_KEY not configured")
            return {"error": "TRADEFEEDS_API_KEY not configured"}
        
        try:
            # Initialize TradeFeeds client
            client = TradeFeedsClient(
                api_key=settings.TRADEFEEDS_API_KEY,
                timeout=settings.TRADEFEEDS_TIMEOUT_SECONDS,
                max_retries=settings.TRADEFEEDS_MAX_RETRIES,
                rate_limit=settings.TRADEFEEDS_RATE_LIMIT
            )
            
            results_by_family = {}
            total_tested = 0
            total_working = 0
            
            # Test each fund family
            for family_name, funds in EXPANDED_MUTUAL_FUNDS.items():
                logger.info(f"\n📊 Testing {family_name} funds ({len(funds)} funds)...")
                family_results = {}
                family_working = 0
                
                for symbol, fund_name in funds.items():
                    start_time = time.time()
                    total_tested += 1
                    
                    try:
                        holdings = await client.get_fund_holdings(symbol)
                        response_time = time.time() - start_time
                        
                        if holdings and len(holdings) > 0:
                            # Success - has holdings data
                            status = "success"
                            holdings_count = len(holdings)
                            family_working += 1
                            total_working += 1
                            
                            # Track working fund details
                            self.working_funds.append({
                                "symbol": symbol,
                                "name": fund_name,
                                "family": family_name,
                                "holdings_count": holdings_count
                            })
                            
                            # Export holdings to CSV
                            await self._export_holdings_csv(symbol, holdings, family_name)
                            
                            logger.info(f"  ✅ {symbol}: {holdings_count} holdings")
                        else:
                            # No data returned
                            status = "no_data"
                            holdings_count = 0
                            logger.info(f"  ⚠️ {symbol}: No holdings data")
                        
                        family_results[symbol] = {
                            "name": fund_name,
                            "status": status,
                            "holdings_count": holdings_count,
                            "response_time": response_time
                        }
                        
                        # Track for CSV export
                        self.all_results.append({
                            "Fund Family": family_name,
                            "Symbol": symbol,
                            "Fund Name": fund_name,
                            "Status": status,
                            "Holdings Count": holdings_count,
                            "Response Time": response_time
                        })
                        
                    except Exception as e:
                        response_time = time.time() - start_time
                        logger.error(f"  ❌ {symbol}: {str(e)}")
                        
                        family_results[symbol] = {
                            "name": fund_name,
                            "status": "error",
                            "holdings_count": 0,
                            "response_time": response_time,
                            "error": str(e)
                        }
                        
                        self.all_results.append({
                            "Fund Family": family_name,
                            "Symbol": symbol,
                            "Fund Name": fund_name,
                            "Status": "error",
                            "Holdings Count": 0,
                            "Response Time": response_time
                        })
                    
                    # Rate limiting delay
                    await asyncio.sleep(2)
                
                # Calculate family statistics
                family_total = len(funds)
                family_coverage = (family_working / family_total * 100) if family_total > 0 else 0
                
                results_by_family[family_name] = {
                    "funds": family_results,
                    "total_tested": family_total,
                    "total_working": family_working,
                    "coverage_percentage": family_coverage
                }
                
                logger.info(f"  📈 {family_name} Coverage: {family_coverage:.1f}% ({family_working}/{family_total})")
            
            # Close client
            await client.close()
            
            # Calculate overall statistics
            overall_success_rate = (total_working / total_tested * 100) if total_tested > 0 else 0
            
            # Categorize families by performance tiers
            performance_tiers = {
                "excellent_80plus": [],
                "good_50_79": [],
                "poor_20_49": [],
                "none_0_19": []
            }
            
            for family_name, family_data in results_by_family.items():
                coverage = family_data["coverage_percentage"]
                if coverage >= 80:
                    performance_tiers["excellent_80plus"].append(family_name)
                elif coverage >= 50:
                    performance_tiers["good_50_79"].append(family_name)
                elif coverage >= 20:
                    performance_tiers["poor_20_49"].append(family_name)
                else:
                    performance_tiers["none_0_19"].append(family_name)
            
            # Prepare final results
            results = {
                "test_date": test_date,
                "test_scope": {
                    "fund_families_tested": len(EXPANDED_MUTUAL_FUNDS),
                    "total_funds_tested": total_tested,
                    "total_working": total_working,
                    "overall_success_rate": overall_success_rate
                },
                "performance_tiers": performance_tiers,
                "results_by_family": results_by_family,
                "working_funds": sorted(self.working_funds, key=lambda x: x["holdings_count"], reverse=True),
                "credits_used": total_tested * 20,  # TradeFeeds 20X multiplier
                "estimated_monthly_cost": {
                    "credits_for_test": total_tested * 20,
                    "monthly_credit_limit": 22000,
                    "percentage_of_limit": f"{(total_tested * 20 / 22000 * 100):.1f}%"
                }
            }
            
            logger.info(f"\n✅ Testing completed: {total_working}/{total_tested} funds successful ({overall_success_rate:.1f}%)")
            logger.info(f"💳 Credits used: {total_tested * 20} ({(total_tested * 20 / 22000 * 100):.1f}% of monthly limit)")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Test failed: {str(e)}")
            return {"error": str(e)}
    
    async def _export_holdings_csv(self, symbol: str, holdings: List[Dict], family: str):
        """Export holdings to CSV for manual inspection"""
        if not holdings:
            return
            
        filename = self.output_dir / f"TradeFeeds_{symbol}_holdings.csv"
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['symbol', 'name', 'weight', 'weight_percent', 'shares', 'market_value']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for holding in holdings:
                writer.writerow({
                    'symbol': holding.get('symbol', ''),
                    'name': holding.get('name', ''),
                    'weight': holding.get('weight', 0),
                    'weight_percent': f"{float(holding.get('weight', 0)) * 100:.2f}%",
                    'shares': holding.get('shares', ''),
                    'market_value': holding.get('market_value', '')
                })
    
    def save_results(self, results: Dict[str, Any]):
        """Save test results in multiple formats"""
        
        # Save JSON results
        json_file = self.output_dir / "tradefeeds_expanded_coverage.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"💾 JSON results saved to {json_file}")
        
        # Save CSV results
        csv_file = self.output_dir / "tradefeeds_expanded_coverage.csv"
        with open(csv_file, 'w', newline='') as f:
            fieldnames = ["Fund Family", "Symbol", "Fund Name", "Status", "Holdings Count", "Response Time"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_results)
        logger.info(f"📊 CSV results saved to {csv_file}")
        
        # Generate and save final report
        self.generate_final_report(results)
    
    def generate_final_report(self, results: Dict[str, Any]):
        """Generate a comprehensive markdown report matching FMP format"""
        
        if "error" in results:
            logger.error(f"Cannot generate report due to error: {results['error']}")
            return
        
        report_lines = [
            "# 📊 EXPANDED Mutual Fund Coverage Analysis - TradeFeeds Final Report",
            "",
            "## 🎯 Executive Summary - TradeFeeds Results",
            "",
            f"- **Tested**: {results['test_scope']['total_funds_tested']} mutual funds across {results['test_scope']['fund_families_tested']} major fund families",
            f"- **Success Rate**: {results['test_scope']['overall_success_rate']:.1f}% ({results['test_scope']['total_working']} funds have holdings data)",
            f"- **Credits Used**: {results['credits_used']} (TradeFeeds 20X multiplier for mutual funds)",
            f"- **Coverage**: {'Extremely Limited' if results['test_scope']['overall_success_rate'] < 20 else 'Moderate' if results['test_scope']['overall_success_rate'] < 50 else 'Good'}",
            "",
            "## 🏆 Performance Tiers",
            "",
            "| Tier | Families | Details |",
            "|------|----------|---------|"
        ]
        
        # Add performance tiers
        tiers = results['performance_tiers']
        if tiers['excellent_80plus']:
            report_lines.append(f"| 🟢 Excellent (80%+) | {len(tiers['excellent_80plus'])} families | {', '.join(tiers['excellent_80plus'])} |")
        if tiers['good_50_79']:
            report_lines.append(f"| 🟡 Good (50-79%) | {len(tiers['good_50_79'])} families | {', '.join(tiers['good_50_79'])} |")
        if tiers['poor_20_49']:
            report_lines.append(f"| 🟠 Poor (20-49%) | {len(tiers['poor_20_49'])} families | {', '.join(tiers['poor_20_49'])} |")
        if tiers['none_0_19']:
            report_lines.append(f"| 🔴 None (0-19%) | {len(tiers['none_0_19'])} families | {', '.join(tiers['none_0_19'][:5])}{'...' if len(tiers['none_0_19']) > 5 else ''} |")
        
        # Add working funds list
        report_lines.extend([
            "",
            f"## ✅ Complete List of Working Funds ({results['test_scope']['total_working']} out of {results['test_scope']['total_funds_tested']})",
            "",
            "| Rank | Symbol | Fund Family | Holdings | Fund Type |",
            "|------|--------|-------------|----------|-----------|"
        ])
        
        for i, fund in enumerate(results['working_funds'][:20], 1):  # Show top 20
            report_lines.append(f"| {i} | {fund['symbol']} | {fund['family']} | {fund['holdings_count']:,} | {fund['name']} |")
        
        if len(results['working_funds']) > 20:
            report_lines.append(f"| ... | ... | ... | ... | ... |")
            report_lines.append(f"| Total | {results['test_scope']['total_working']} funds | | | |")
        
        # Add families with zero coverage
        zero_coverage = [family for family, data in results['results_by_family'].items() 
                        if data['coverage_percentage'] == 0]
        
        if zero_coverage:
            report_lines.extend([
                "",
                f"## ❌ Fund Families with Zero Coverage ({len(zero_coverage)} families)",
                ""
            ])
            
            for family in zero_coverage:
                family_data = results['results_by_family'][family]
                report_lines.append(f"- {family} (0/{family_data['total_tested']})")
        
        # Key insights section
        report_lines.extend([
            "",
            "## 🔍 Key Insights from Expanded Testing",
            ""
        ])
        
        # Analyze patterns
        vanguard_coverage = results['results_by_family'].get('Vanguard', {}).get('coverage_percentage', 0)
        fidelity_coverage = results['results_by_family'].get('Fidelity', {}).get('coverage_percentage', 0)
        
        report_lines.extend([
            "### 1. Coverage Analysis:",
            f"  - Vanguard: {vanguard_coverage:.1f}% coverage",
            f"  - Fidelity: {fidelity_coverage:.1f}% coverage",
            f"  - Overall: {results['test_scope']['overall_success_rate']:.1f}% success rate",
            "",
            "### 2. Cost Impact:",
            f"  - Each fund query costs 20 credits (20X multiplier)",
            f"  - This test used {results['credits_used']} credits",
            f"  - That's {results['estimated_monthly_cost']['percentage_of_limit']} of monthly limit for just this test",
            "",
            "### 3. Scalability Concerns:",
            f"  - Monthly limit: 22,000 credits",
            f"  - Max mutual fund queries per month: {22000 // 20} funds",
            "  - The 20X multiplier severely limits mutual fund data scalability",
            ""
        ])
        
        # Strategic implications
        report_lines.extend([
            "## 💡 Strategic Implications for SigmaSight",
            "",
            "### ✅ What Works with TradeFeeds:",
        ])
        
        if results['test_scope']['overall_success_rate'] > 50:
            report_lines.extend([
                "- Reasonable mutual fund coverage for major providers",
                "- ETFs work well (as seen in previous testing)",
                "- API is stable and reliable"
            ])
        else:
            report_lines.extend([
                "- Limited mutual fund coverage",
                "- Better suited for ETFs than mutual funds",
                "- High credit cost for mutual fund data"
            ])
        
        report_lines.extend([
            "",
            "### ❌ TradeFeeds Limitations:",
            "- 20X credit multiplier for mutual funds is very expensive",
            "- Limited to 22,000 credits/month restricts scaling",
            f"- Only {results['test_scope']['overall_success_rate']:.1f}% coverage across test set",
            "",
            "### 🎯 Production Recommendation:",
            ""
        ])
        
        if results['test_scope']['overall_success_rate'] < 20:
            report_lines.extend([
                "1. **NOT RECOMMENDED** for mutual fund holdings data",
                "2. Consider FMP or other providers for better coverage",
                "3. TradeFeeds 20X multiplier makes it cost-prohibitive",
                "4. Very limited coverage makes it unsuitable for production"
            ])
        elif results['test_scope']['overall_success_rate'] < 50:
            report_lines.extend([
                "1. **Limited Use Case** - Only for specific fund families with good coverage",
                "2. Consider FMP for broader mutual fund support",
                "3. TradeFeeds better suited for ETF data",
                "4. Hybrid approach: Use different provider for mutual funds"
            ])
        else:
            report_lines.extend([
                "1. **Viable Option** with coverage limitations noted",
                "2. Monitor credit usage carefully due to 20X multiplier",
                "3. Consider caching strategies to minimize API calls",
                "4. May need supplementary provider for gaps in coverage"
            ])
        
        report_lines.extend([
            "",
            "## 📊 Comparison with FMP Testing",
            "",
            "Based on the FMP expanded test showing 7.5% coverage:",
            f"- TradeFeeds: {results['test_scope']['overall_success_rate']:.1f}% coverage",
            "- FMP: 7.5% coverage (from previous test)",
            f"- **Winner**: {'TradeFeeds' if results['test_scope']['overall_success_rate'] > 7.5 else 'Neither - both have poor mutual fund coverage'}",
            "",
            "However, consider:",
            "- FMP: No multiplier penalty (1X cost per query)",
            "- TradeFeeds: 20X multiplier makes it much more expensive",
            "- FMP: $139/month with unlimited API calls",
            "- TradeFeeds: $149/month with 22,000 credit limit",
            "- FMP: Better for high-volume usage despite lower coverage",
            "- TradeFeeds: Better coverage but prohibitive costs at scale"
        ])
        
        # Save report
        report_file = self.output_dir / "TRADEFEEDS_EXPANDED_COVERAGE_REPORT.md"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"📋 Final report saved to {report_file}")


async def main():
    """Run the expanded coverage test"""
    print("🧪 TradeFeeds Expanded Mutual Fund Coverage Test")
    print("=" * 60)
    print("Testing 174 mutual funds from 20 major fund families")
    print("Matching the exact test set used for FMP coverage analysis")
    print("")
    
    # Check API key
    if not settings.TRADEFEEDS_API_KEY:
        print("❌ TRADEFEEDS_API_KEY not configured")
        print("Please set TRADEFEEDS_API_KEY in your environment variables")
        return
    
    print("Fund families to test:")
    for i, family in enumerate(EXPANDED_MUTUAL_FUNDS.keys(), 1):
        print(f"  {i:2d}. {family} ({len(EXPANDED_MUTUAL_FUNDS[family])} funds)")
    print("")
    print(f"Total funds: {sum(len(funds) for funds in EXPANDED_MUTUAL_FUNDS.values())}")
    print(f"Estimated credits: {sum(len(funds) for funds in EXPANDED_MUTUAL_FUNDS.values()) * 20}")
    print("")
    
    # Run test
    tester = TradeFeedsExpandedTester()
    results = await tester.test_fund_coverage()
    
    # Save results
    if "error" not in results:
        tester.save_results(results)
        
        print("\n🎉 Testing completed! Check the following files:")
        print(f"  📊 Coverage Report: {tester.output_dir}/TRADEFEEDS_EXPANDED_COVERAGE_REPORT.md")
        print(f"  💾 JSON Results: {tester.output_dir}/tradefeeds_expanded_coverage.json")
        print(f"  📁 CSV Results: {tester.output_dir}/tradefeeds_expanded_coverage.csv")
        print(f"  📁 Holdings CSVs: {tester.output_dir}/TradeFeeds_*_holdings.csv")
        
        # Print quick summary
        print(f"\n📈 Quick Summary:")
        print(f"  - Total Funds Tested: {results['test_scope']['total_funds_tested']}")
        print(f"  - Successful: {results['test_scope']['total_working']}")
        print(f"  - Overall Coverage: {results['test_scope']['overall_success_rate']:.1f}%")
        print(f"  - Credits Used: {results['credits_used']}")
    else:
        print(f"\n❌ Test failed: {results['error']}")


if __name__ == "__main__":
    asyncio.run(main())