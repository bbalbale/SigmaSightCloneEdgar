"""
Test API endpoint directly to see if tags are returned
"""

import asyncio
import requests
import json

# Login and get token
def login():
    response = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        json={"email": "demo_hedgefundstyle@sigmasight.com", "password": "demo12345"}
    )
    data = response.json()
    return data["access_token"]

# Get positions with details
def get_positions(token, portfolio_id):
    response = requests.get(
        f"http://localhost:8000/api/v1/data/positions/details?portfolio_id={portfolio_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()

def main():
    # Login
    token = login()

    # Use the hedge fund portfolio ID we know from the database
    portfolio_id = "fcd71196-e93e-f000-5a74-31a9eead3118"
    print(f"Using Hedge Fund Portfolio ID: {portfolio_id}")

    # Get positions
    data = get_positions(token, portfolio_id)

    print(f"\nTotal positions: {len(data['positions'])}")

    # Check tags on positions
    positions_with_tags = 0
    for pos in data['positions']:
        if 'tags' in pos and pos['tags']:
            positions_with_tags += 1
            print(f"\n{pos['symbol']:15} has {len(pos['tags'])} tags:")
            for tag in pos['tags']:
                print(f"  - {tag['name']} (color: {tag['color']})")

    print(f"\n\nSummary: {positions_with_tags} out of {len(data['positions'])} positions have tags")

    # Show raw JSON for first position with tags
    for pos in data['positions']:
        if 'tags' in pos and pos['tags']:
            print(f"\n\nRaw JSON for {pos['symbol']}:")
            print(json.dumps(pos, indent=2))
            break

if __name__ == "__main__":
    main()