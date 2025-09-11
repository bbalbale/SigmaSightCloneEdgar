#!/usr/bin/env python
"""
Generate portfolio reports for all three demo portfolios
"""
import asyncio
from datetime import date
from app.database import get_async_session
from app.reports.portfolio_report_generator import PortfolioReportGenerator

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Demo portfolio IDs (from TODO2.md)
DEMO_PORTFOLIOS = {
    "Demo Individual Investor Portfolio": "51134ffd-2f13-49bd-b1f5-0c327e801b69",
    "Demo High Net Worth Investor Portfolio": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
    "Demo Hedge Fund Style Investor Portfolio": "2ee7435f-379f-4606-bdb7-dadce587a182"
}

async def generate_all_reports():
    """Generate reports for all demo portfolios"""
    print("=" * 80)
    print("📊 Generating Portfolio Reports for All Demo Portfolios")
    print("=" * 80)
    
    async with get_async_session() as db:
        generator = PortfolioReportGenerator(db)
        report_date = date.today()
        
        for name, portfolio_id in DEMO_PORTFOLIOS.items():
            print(f"\n📈 Generating reports for: {name}")
            print(f"   Portfolio ID: {portfolio_id}")
            print("-" * 40)
            
            try:
                # The generate_portfolio_report function handles all formats and file writing
                from app.reports.portfolio_report_generator import generate_portfolio_report, ReportRequest
                
                print(f"   Generating all formats (MD, JSON, CSV)...")
                request = ReportRequest(
                    portfolio_id=portfolio_id,
                    as_of=report_date,
                    formats=['md', 'json', 'csv'],
                    write_to_disk=True
                )
                result = await generate_portfolio_report(db, request)
                print(f"   ✅ All formats generated")
                
                # Create a nice folder name
                folder_name = name.lower().replace(' ', '-').replace('investor-', '').replace('style-', '')
                print(f"   📁 Reports saved to: reports/{folder_name}_{report_date}/")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 80)
    print("✅ Report generation complete!")
    print("📁 All reports saved in: reports/")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(generate_all_reports())