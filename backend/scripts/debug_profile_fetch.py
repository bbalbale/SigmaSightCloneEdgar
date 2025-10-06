import asyncio
from app.services.yahooquery_profile_fetcher import fetch_company_profiles

async def main():
    # Test with a single symbol
    profiles = await fetch_company_profiles(['AAPL'])
    print("\n=== Fetched Profiles ===")
    for symbol, data in profiles.items():
        print(f"\nSymbol: {symbol}")
        print(f"Company Name: {data.get('company_name')}")
        print(f"Sector: {data.get('sector')}")
        print(f"Industry: {data.get('industry')}")
        print(f"All keys: {list(data.keys())[:15]}")

if __name__ == "__main__":
    asyncio.run(main())
