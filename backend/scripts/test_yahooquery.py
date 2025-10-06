from yahooquery import Ticker

# Test with a single symbol
ticker = Ticker('AAPL')

print("=== Testing where company name exists ===\n")

# Check summary_profile
print("1. summary_profile:")
sp = ticker.summary_profile
if isinstance(sp, dict) and 'AAPL' in sp:
    print(f"   Keys: {sp['AAPL'].keys() if isinstance(sp['AAPL'], dict) else 'Not a dict'}")
    print(f"   longName: {sp['AAPL'].get('longName', 'NOT FOUND')}")

# Check summary_detail
print("\n2. summary_detail:")
sd = ticker.summary_detail
if isinstance(sd, dict) and 'AAPL' in sd:
    print(f"   Keys: {sd['AAPL'].keys() if isinstance(sd['AAPL'], dict) else 'Not a dict'}")
    print(f"   longName: {sd['AAPL'].get('longName', 'NOT FOUND')}")

# Check price
print("\n3. price:")
price = ticker.price
if isinstance(price, dict) and 'AAPL' in price:
    print(f"   Keys: {price['AAPL'].keys() if isinstance(price['AAPL'], dict) else 'Not a dict'}")
    print(f"   longName: {price['AAPL'].get('longName', 'NOT FOUND')}")
    print(f"   shortName: {price['AAPL'].get('shortName', 'NOT FOUND')}")

# Check asset_profile
print("\n4. asset_profile:")
ap = ticker.asset_profile
if isinstance(ap, dict) and 'AAPL' in ap:
    print(f"   Keys: {list(ap['AAPL'].keys())[:10] if isinstance(ap['AAPL'], dict) else 'Not a dict'}")
    print(f"   longName: {ap['AAPL'].get('longName', 'NOT FOUND')}")

# Check quote_type
print("\n5. quote_type:")
qt = ticker.quote_type
if isinstance(qt, dict) and 'AAPL' in qt:
    print(f"   Keys: {qt['AAPL'].keys() if isinstance(qt['AAPL'], dict) else 'Not a dict'}")
    print(f"   longName: {qt['AAPL'].get('longName', 'NOT FOUND')}")
