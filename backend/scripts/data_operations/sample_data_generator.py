"""
Sample data generator for testing and demo purposes
"""
import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import csv
import json

def generate_sample_portfolio_csv(filename: str = "sample_portfolio.csv", num_positions: int = 50):
    """
    Generate a sample portfolio CSV file
    """
    print(f"Generating sample portfolio CSV with {num_positions} positions...")
    
    # Sample tickers for different asset classes
    stock_tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX", "SPY", "QQQ"]
    option_tickers = ["AAPL240315C00150000", "GOOGL240315P00120000", "MSFT240315C00300000"]
    
    positions = []
    
    for i in range(num_positions):
        # 80% stocks, 20% options
        if random.random() < 0.8:
            ticker = random.choice(stock_tickers)
            quantity = random.randint(10, 1000)
            entry_price = round(random.uniform(50, 500), 2)
        else:
            ticker = random.choice(option_tickers)
            quantity = random.randint(1, 50)
            entry_price = round(random.uniform(1, 50), 2)
        
        # Random entry date within last 90 days
        entry_date = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
        
        # Random tags
        tags = random.choice([
            "growth,tech",
            "value,dividend",
            "momentum",
            "hedge,protection",
            "core,long-term",
            ""
        ])
        
        positions.append({
            "ticker": ticker,
            "quantity": quantity,
            "entry_price": entry_price,
            "entry_date": entry_date,
            "tags": tags
        })
    
    # Write to CSV
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['ticker', 'quantity', 'entry_price', 'entry_date', 'tags']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(positions)
    
    print(f"Sample portfolio CSV generated: {filename}")
    return positions

def generate_mock_greeks_data() -> Dict[str, Any]:
    """Generate mock Greeks data for options positions"""
    return {
        "delta": round(random.uniform(-1, 1), 4),
        "gamma": round(random.uniform(0, 0.1), 4),
        "theta": round(random.uniform(-0.5, 0), 4),
        "vega": round(random.uniform(0, 1), 4),
        "rho": round(random.uniform(-0.1, 0.1), 4)
    }

def generate_mock_risk_metrics() -> Dict[str, Any]:
    """Generate mock risk metrics for portfolio"""
    return {
        "var_95": round(random.uniform(10000, 100000), 2),
        "var_99": round(random.uniform(20000, 200000), 2),
        "expected_shortfall": round(random.uniform(15000, 150000), 2),
        "volatility": round(random.uniform(0.1, 0.4), 4),
        "sharpe_ratio": round(random.uniform(0.5, 2.0), 4),
        "max_drawdown": round(random.uniform(0.05, 0.3), 4)
    }

def generate_mock_factor_exposures() -> Dict[str, float]:
    """Generate mock factor exposures"""
    factors = [
        "Market", "Size", "Value", "Momentum", 
        "Quality", "Volatility", "Dividend", "Short Interest"
    ]
    
    return {
        factor: round(random.uniform(-2, 2), 4) 
        for factor in factors
    }

if __name__ == "__main__":
    # Generate sample data
    generate_sample_portfolio_csv("sample_portfolio.csv", 50)
    
    # Generate and save mock data examples
    mock_data = {
        "greeks": generate_mock_greeks_data(),
        "risk_metrics": generate_mock_risk_metrics(),
        "factor_exposures": generate_mock_factor_exposures()
    }
    
    with open("mock_data_examples.json", "w") as f:
        json.dump(mock_data, f, indent=2)
    
    print("Sample data generation completed!")
