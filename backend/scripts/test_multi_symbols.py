from yahooquery import Ticker

# Test with multiple symbols
symbols = ['AAPL', 'MSFT', 'META', 'PG']
ticker = Ticker(symbols, asynchronous=True)

print("=== Testing quote_type with multiple symbols ===\n")

quote_type = ticker.quote_type

for symbol in symbols:
    print(f"{symbol}:")
    if isinstance(quote_type, dict) and symbol in quote_type:
        qt = quote_type[symbol]
        print(f"  Type: {type(qt)}")
        if isinstance(qt, dict):
            print(f"  Has longName: {'longName' in qt}")
            print(f"  longName value: {qt.get('longName')}")
            print(f"  First 5 keys: {list(qt.keys())[:5]}")
        else:
            print(f"  Not a dict: {qt}")
    else:
        print(f"  Not in quote_type")
    print()
