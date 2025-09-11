#!/usr/bin/env python
"""Test script for Portfolio Report Generator data collection."""

import asyncio
import json
from datetime import date
from app.database import get_async_session
from app.reports.portfolio_report_generator import generate_portfolio_report, ReportRequest


async def test_report_generation():
    """Test report generation with demo portfolio."""
    
    # Use Demo Individual Investor Portfolio
    portfolio_id = "51134ffd-2f13-49bd-b1f5-0c327e801b69"
    
    async with get_async_session() as db:
        # Create report request
        request = ReportRequest(
            portfolio_id=portfolio_id,
            as_of=date.today(),
            formats=["md", "json", "csv"]
        )
        
        print(f"🚀 Generating report for portfolio: {portfolio_id}")
        print(f"   As of: {request.as_of}")
        print(f"   Formats: {list(request.formats)}")
        print("-" * 60)
        
        # Generate report
        artifacts = await generate_portfolio_report(db, request)
        
        # Display results
        if "md" in artifacts:
            print("\n📝 MARKDOWN REPORT:")
            print("-" * 60)
            print(artifacts["md"])
        
        if "json" in artifacts:
            print("\n📊 JSON REPORT (preview):")
            print("-" * 60)
            # Pretty print JSON with proper formatting
            json_str = json.dumps(artifacts["json"], indent=2, default=str)
            # Limit output for readability
            lines = json_str.split('\n')
            if len(lines) > 50:
                print('\n'.join(lines[:50]))
                print(f"... ({len(lines) - 50} more lines)")
            else:
                print(json_str)
        
        if "csv" in artifacts:
            print("\n📊 CSV REPORT:")
            print("-" * 60)
            print(artifacts["csv"])
        
        # Summary
        print("\n✅ REPORT GENERATION SUMMARY:")
        print("-" * 60)
        print(f"   Formats generated: {list(artifacts.keys())}")
        
        # Check data completeness
        if "json" in artifacts:
            data = artifacts["json"]
            if "meta" in data:
                meta = data.get("meta", {})
                if "error" not in meta:
                    print(f"   Portfolio: {meta.get('portfolio_name')}")
                    
                    # Check what data we have
                    sections = data.get("sections", {})
                    if isinstance(sections, dict) and not sections:
                        # Using our actual data structure
                        if data.get("portfolio"):
                            print(f"   Positions: {data['portfolio'].get('position_count', 0)}")
                        if data.get("snapshot"):
                            print(f"   Snapshot date: {data['snapshot'].get('date')}")
                        if data.get("exposures"):
                            print(f"   Gross exposure: ${data['exposures'].get('gross_exposure', 0):,.2f}")
                        if data.get("greeks"):
                            print(f"   Portfolio delta: {data['greeks'].get('delta', 0):.4f}")
                else:
                    print(f"   ⚠️ Error: {meta.get('error')}")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Portfolio Report Generator Test")
    print("=" * 60)
    asyncio.run(test_report_generation())