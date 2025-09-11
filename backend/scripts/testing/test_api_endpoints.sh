#!/bin/bash

# API Testing Script for SigmaSight Market Data Endpoints
# Usage: ./test_api_endpoints.sh [BASE_URL]

BASE_URL=${1:-"http://localhost:8000"}
echo "🚀 Testing SigmaSight Market Data API endpoints"
echo "Base URL: $BASE_URL"
echo "=" $(printf '%*s' 50 '' | tr ' ' '=')

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test an endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local auth_header=$4
    local data=$5
    
    echo -e "\n🔍 Testing: $description"
    echo "   $method $endpoint"
    
    if [ "$method" = "GET" ]; then
        if [ -n "$auth_header" ]; then
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -H "$auth_header" "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$BASE_URL$endpoint")
        fi
    elif [ "$method" = "POST" ]; then
        if [ -n "$auth_header" ]; then
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST -H "Content-Type: application/json" -H "$auth_header" -d "$data" "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
        fi
    fi
    
    # Extract HTTP status code
    http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$response" | sed -e 's/HTTPSTATUS:.*//g')
    
    # Check status code
    if [ "$http_code" -eq 200 ]; then
        echo -e "   ${GREEN}✅ Status: $http_code${NC}"
    elif [ "$http_code" -eq 401 ]; then
        echo -e "   ${YELLOW}🔒 Status: $http_code (Authentication required)${NC}"
    else
        echo -e "   ${RED}❌ Status: $http_code${NC}"
    fi
    
    # Show response snippet
    if [ ${#body} -gt 100 ]; then
        echo "   Response: $(echo "$body" | cut -c1-100)..."
    else
        echo "   Response: $body"
    fi
}

# Function to get auth token
get_auth_token() {
    echo -e "\n🔐 Getting authentication token..."
    
    # Try to login with demo user
    login_data='{"email": "demo_growth@sigmasight.com", "password": "demopassword123"}'
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST -H "Content-Type: application/json" -d "$login_data" "$BASE_URL/api/v1/auth/login")
    
    http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$response" | sed -e 's/HTTPSTATUS:.*//g')
    
    if [ "$http_code" -eq 200 ]; then
        # Extract token from JSON response
        token=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        if [ -n "$token" ]; then
            echo -e "   ${GREEN}✅ Login successful${NC}"
            echo "Authorization: Bearer $token"
            return 0
        fi
    fi
    
    echo -e "   ${YELLOW}⚠️  Login failed (demo user may not exist)${NC}"
    echo "   You can:"
    echo "   1. Run: python scripts/seed_demo_users.py"
    echo "   2. Test endpoints without auth (they should return 401)"
    return 1
}

# Test basic health endpoints first
echo -e "\n📋 Testing Basic Endpoints:"
test_endpoint "GET" "/" "Root endpoint"
test_endpoint "GET" "/health" "Health check"

# Test authentication
AUTH_HEADER=""
if get_auth_token; then
    read -r AUTH_HEADER
fi

# Test Market Data Endpoints
echo -e "\n📊 Testing Market Data Endpoints:"

# Test without authentication first
test_endpoint "GET" "/api/v1/market-data/prices/AAPL" "Price data (no auth)"
test_endpoint "GET" "/api/v1/market-data/current-prices?symbols=AAPL&symbols=MSFT" "Current prices (no auth)"

# Test with authentication if available
if [ -n "$AUTH_HEADER" ]; then
    echo -e "\n📊 Testing Market Data Endpoints (Authenticated):"
    test_endpoint "GET" "/api/v1/market-data/prices/AAPL" "Price data for AAPL" "$AUTH_HEADER"
    test_endpoint "GET" "/api/v1/market-data/current-prices?symbols=AAPL&symbols=MSFT" "Current prices" "$AUTH_HEADER"
    test_endpoint "GET" "/api/v1/market-data/sectors?symbols=AAPL" "GICS sector data" "$AUTH_HEADER"
    test_endpoint "GET" "/api/v1/market-data/options/AAPL" "Options chain for AAPL" "$AUTH_HEADER"
    
    # Test refresh endpoint
    refresh_data='{"symbols": ["AAPL"], "days_back": 5}'
    test_endpoint "POST" "/api/v1/market-data/refresh" "Market data refresh" "$AUTH_HEADER" "$refresh_data"
fi

# Test Other API Endpoints
echo -e "\n🏦 Testing Other Endpoints:"
test_endpoint "GET" "/api/v1/portfolio/" "Portfolio overview"
test_endpoint "GET" "/api/v1/positions" "Positions list"
test_endpoint "GET" "/api/v1/risk/metrics" "Risk metrics"

# Summary
echo -e "\n" $(printf '%*s' 50 '' | tr ' ' '=')
echo "📋 Test Complete!"
echo ""
echo "Next steps:"
echo "1. If you see 401 errors, run: python scripts/seed_demo_users.py"
echo "2. Add your Polygon API key to .env file"
echo "3. Run: python scripts/test_market_data.py for detailed testing"
echo "4. Start the server: uvicorn app.main:app --reload"